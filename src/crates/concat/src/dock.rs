// SPDX-License-Identifier: AGPL-3.0-or-later
// SPDX-FileCopyrightText: 2026 Jareer and Concat contributors

//! The workspace's arrangement: a tree of splits and views, walked flat
//! for Slint, which has no recursion.

use serde::{Deserialize, Serialize};

use crate::ui::{DockDivider, DockSide, PaneKind, SeatBox};

pub const SEAT_MIN_W: f32 = 240.0;
pub const SEAT_MIN_H: f32 = 140.0;
/// The floor that holds where the one above cannot: enough of a seat left to
/// find its corner button with, which is the only way back from a layout that
/// has been squeezed too far.
pub const SEAT_MIN_GRAB: f32 = 64.0;
/// The gutter between the halves of a split, and the margin round the lot.
pub const SEAT_GAP: f32 = 8.0;
/// The VU meters' column needs only its ruler, its two bars and the
/// padding round them: 26 + 14 + 14 and two gaps of 4, in 6px of padding
/// a side (see meters-pane.slint).
pub const METERS_MIN_W: f32 = 76.0;
/// The meters' share of the bottom row in the default layout: a slim
/// column beside the timeline, at its full height. The row is about two
/// thirds of the window wide, beside the monitor's column.
const METERS_SHARE: f32 = 0.08;

pub enum Dock {
    /// One view, filling its box.
    Leaf(PaneKind),
    /// Two nodes and the gutter between them. `columns` means side by side,
    /// which is a vertical gutter dragged left and right; `ratio` is the share
    /// of the usable extent — the box less the gutter — that the first takes.
    Split {
        columns: bool,
        ratio: f32,
        first: Box<Dock>,
        second: Box<Dock>,
    },
}

impl Dock {
    pub fn leaf(kind: PaneKind) -> Box<Dock> {
        Box::new(Dock::Leaf(kind))
    }

    /// The node a path names, following each step into the first branch or the
    /// second. A path that runs past a leaf stops there, which cannot happen
    /// for a path this module produced.
    pub fn at(&self, path: &[bool]) -> &Dock {
        let Some((step, rest)) = path.split_first() else {
            return self;
        };
        match self {
            Dock::Split { first, second, .. } => {
                if *step {
                    second.at(rest)
                } else {
                    first.at(rest)
                }
            }
            leaf => leaf,
        }
    }

    pub fn at_mut(&mut self, path: &[bool]) -> &mut Dock {
        let Some((step, rest)) = path.split_first() else {
            return self;
        };
        match self {
            Dock::Split { first, second, .. } => {
                if *step {
                    second.at_mut(rest)
                } else {
                    first.at_mut(rest)
                }
            }
            leaf => leaf,
        }
    }

    /// The path to the nth leaf, counted in the same walk `lay_out` uses — so
    /// the number a seat carries and the number a drop reports are the same
    /// number. Paths rather than indices for the editing below, because an
    /// index is invalidated by a change elsewhere in the tree and a path is
    /// only invalidated by a change on its own way down.
    pub fn leaf_path(&self, index: usize) -> Option<Vec<bool>> {
        fn walk(node: &Dock, want: usize, seen: &mut usize, path: &mut Vec<bool>) -> bool {
            match node {
                Dock::Leaf(_) => {
                    if *seen == want {
                        return true;
                    }
                    *seen += 1;
                    false
                }
                Dock::Split { first, second, .. } => {
                    path.push(false);
                    if walk(first, want, seen, path) {
                        return true;
                    }
                    path.pop();
                    path.push(true);
                    if walk(second, want, seen, path) {
                        return true;
                    }
                    path.pop();
                    false
                }
            }
        }
        let (mut seen, mut path) = (0, Vec::new());
        walk(self, index, &mut seen, &mut path).then_some(path)
    }

    /// The same for the nth split — parent before children, which is the order
    /// `lay_out` numbers the gutters in.
    pub fn split_path(&self, index: usize) -> Option<Vec<bool>> {
        fn walk(node: &Dock, want: usize, seen: &mut usize, path: &mut Vec<bool>) -> bool {
            let Dock::Split { first, second, .. } = node else {
                return false;
            };
            if *seen == want {
                return true;
            }
            *seen += 1;
            path.push(false);
            if walk(first, want, seen, path) {
                return true;
            }
            path.pop();
            path.push(true);
            if walk(second, want, seen, path) {
                return true;
            }
            path.pop();
            false
        }
        let (mut seen, mut path) = (0, Vec::new());
        walk(self, index, &mut seen, &mut path).then_some(path)
    }

    pub fn kind_at(&self, index: usize) -> Option<PaneKind> {
        match self.at(&self.leaf_path(index)?) {
            Dock::Leaf(kind) => Some(*kind),
            _ => None,
        }
    }

    /// Turn one leaf into a split, with a new view on the named side of it.
    /// Half and half: the seat being split is the only thing that knows how
    /// much room there is, and half of it is the answer that needs no rule.
    pub fn split_leaf(&mut self, path: &[bool], kind: PaneKind, side: DockSide) {
        let node = self.at_mut(path);
        let existing = Box::new(std::mem::replace(node, Dock::Leaf(kind)));
        let (columns, first, second) = match side {
            DockSide::Left => (true, Dock::leaf(kind), existing),
            DockSide::Right => (true, existing, Dock::leaf(kind)),
            DockSide::Top => (false, Dock::leaf(kind), existing),
            _ => (false, existing, Dock::leaf(kind)),
        };
        *node = Dock::Split {
            columns,
            ratio: 0.5,
            first,
            second,
        };
    }

    /// Take a leaf out, and let its sibling take the space — the split it was
    /// half of stops existing. A path with nothing above it is the whole tree,
    /// which cannot be removed: a window with no seats has nowhere to put
    /// anything back.
    pub fn remove_leaf(&mut self, path: &[bool]) {
        let Some((last, above)) = path.split_last() else {
            return;
        };
        let parent = self.at_mut(above);
        let survivor = match parent {
            Dock::Split { first, second, .. } => {
                let keep = if *last { first } else { second };
                std::mem::replace(keep.as_mut(), Dock::Leaf(PaneKind::Media))
            }
            _ => return,
        };
        *parent = survivor;
    }
}

/// The tree walked flat: a box per view, a box per gutter.
#[derive(Default)]
pub struct DockLayout {
    pub seats: Vec<SeatBox>,
    pub dividers: Vec<DockDivider>,
    /// The usable extent of each split — its box less the gutter — in the same
    /// order as `dividers`. A divider drag is a delta in pixels and a ratio is
    /// a fraction, and this is what converts between them.
    pub extents: Vec<f32>,
}

pub fn lay_out(node: &Dock, (x, y, w, h): (f32, f32, f32, f32), out: &mut DockLayout) {
    match node {
        Dock::Leaf(kind) => out.seats.push(SeatBox {
            index: out.seats.len() as i32,
            kind: *kind,
            x,
            y,
            width: w.max(0.0),
            height: h.max(0.0),
        }),
        Dock::Split {
            columns,
            ratio,
            first,
            second,
        } => {
            // The slot is taken before the children are walked, so a gutter's
            // number is its split's position in a parent-first walk — which is
            // what `split_path` counts and what a drag reports back.
            let index = out.dividers.len();
            out.dividers.push(DockDivider::default());
            out.extents.push(0.0);

            let along = if *columns { w } else { h };
            let usable = (along - SEAT_GAP).max(0.0);
            let head = (usable * ratio).clamp(0.0, usable);
            out.extents[index] = usable;
            out.dividers[index] = if *columns {
                DockDivider {
                    index: index as i32,
                    columns: true,
                    x: x + head,
                    y,
                    width: SEAT_GAP,
                    height: h.max(0.0),
                }
            } else {
                DockDivider {
                    index: index as i32,
                    columns: false,
                    x,
                    y: y + head,
                    width: w.max(0.0),
                    height: SEAT_GAP,
                }
            };

            if *columns {
                lay_out(first, (x, y, head, h), out);
                lay_out(second, (x + head + SEAT_GAP, y, usable - head, h), out);
            } else {
                lay_out(first, (x, y, w, head), out);
                lay_out(second, (x, y + head + SEAT_GAP, w, usable - head), out);
            }
        }
    }
}

/// The arrangement the editor opens with when none was kept: the monitor in
/// a column of its own down the right, the whole height of the window, so a
/// vertical picture is shown as large as it can be; to its left the library
/// and the inspector across the top and the timeline along the bottom. The
/// shares are a phone-video editor's: about two thirds of the width to the
/// working side, a little under half its height to the top row.
pub fn default_dock() -> Dock {
    Dock::Split {
        columns: true,
        ratio: 0.68,
        first: Box::new(Dock::Split {
            columns: false,
            ratio: 0.44,
            first: Box::new(Dock::Split {
                columns: true,
                ratio: 0.54,
                first: Dock::leaf(PaneKind::Media),
                second: Dock::leaf(PaneKind::Inspector),
            }),
            // The timeline, and the VU meters in a slim column beside it.
            second: Box::new(Dock::Split {
                columns: true,
                ratio: 1.0 - METERS_SHARE,
                first: Dock::leaf(PaneKind::Timeline),
                second: Dock::leaf(PaneKind::Meters),
            }),
        }),
        second: Dock::leaf(PaneKind::Preview),
    }
}

/// A dock as the preferences keep it, so the next launch opens on the
/// arrangement the person left. Panes are named rather than numbered, so a
/// file written by this build still reads after a pane is added.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "camelCase")]
pub enum SavedDock {
    /// One view.
    Leaf {
        /// The pane's name; see [`pane_name`].
        pane: String,
    },
    /// Two nodes side by side (`columns`) or stacked, `ratio` to the first.
    Split {
        columns: bool,
        ratio: f32,
        first: Box<SavedDock>,
        second: Box<SavedDock>,
    },
}

fn pane_name(kind: PaneKind) -> &'static str {
    match kind {
        PaneKind::Media => "media",
        PaneKind::Preview => "preview",
        PaneKind::Inspector => "inspector",
        PaneKind::Timeline => "timeline",
        PaneKind::Keyframes => "keyframes",
        PaneKind::Meters => "meters",
    }
}

fn pane_of(name: &str) -> Option<PaneKind> {
    Some(match name {
        "media" => PaneKind::Media,
        "preview" => PaneKind::Preview,
        "inspector" => PaneKind::Inspector,
        "timeline" => PaneKind::Timeline,
        "keyframes" => PaneKind::Keyframes,
        "meters" => PaneKind::Meters,
        _ => return None,
    })
}

impl Dock {
    /// The dock as the preferences write it.
    pub fn to_saved(&self) -> SavedDock {
        match self {
            Dock::Leaf(kind) => SavedDock::Leaf {
                pane: pane_name(*kind).to_owned(),
            },
            Dock::Split {
                columns,
                ratio,
                first,
                second,
            } => SavedDock::Split {
                columns: *columns,
                ratio: *ratio,
                first: Box::new(first.to_saved()),
                second: Box::new(second.to_saved()),
            },
        }
    }

    /// A kept dock read back, or None when it names a pane this build does
    /// not know or a share outside the split - a hand-edited or damaged
    /// file opens on the default rather than on a broken window.
    pub fn from_saved(saved: &SavedDock) -> Option<Dock> {
        match saved {
            SavedDock::Leaf { pane } => pane_of(pane).map(Dock::Leaf),
            SavedDock::Split {
                columns,
                ratio,
                first,
                second,
            } => {
                if !ratio.is_finite() || *ratio <= 0.0 || *ratio >= 1.0 {
                    return None;
                }
                Some(Dock::Split {
                    columns: *columns,
                    ratio: *ratio,
                    first: Box::new(Dock::from_saved(first)?),
                    second: Box::new(Dock::from_saved(second)?),
                })
            }
        }
    }
}

/// The top edge of a row, measured down the stack from the first lane.
/// The dock a narrow window shows: the monitor over the timeline, and
/// nothing beside either. The library and the inspector are a switch away
/// on each seat - see `PaneSwitcher` - which on a phone is how they are
/// reached in every editor: one at a time, in the space the picture had.
pub fn compact_dock() -> Dock {
    Dock::Split {
        columns: false,
        ratio: 0.5,
        first: Dock::leaf(PaneKind::Preview),
        second: Dock::leaf(PaneKind::Timeline),
    }
}

pub fn row_top(heights: &[f32], row: i32) -> f32 {
    heights.iter().take(row.max(0) as usize).sum()
}

/// The row a point down the stack falls in, clamped to the stack.
pub fn row_at(heights: &[f32], y: f32) -> i32 {
    let mut top = 0.0;
    for (row, height) in heights.iter().enumerate() {
        top += height;
        if y < top {
            return row as i32;
        }
    }
    (heights.len() as i32 - 1).max(0)
}

/// The row whose top edge is nearest a point down the stack.
///
/// What a *move* wants, and not the same question as `row_at`: dragging a clip
/// halfway into the lane below should put it there, which is the rounding the
/// old `delta / lane-height` did for free back when every lane was one height.
pub fn nearest_row(heights: &[f32], y: f32) -> i32 {
    let (mut top, mut best, mut best_distance) = (0.0_f32, 0_i32, f32::MAX);
    for (row, height) in heights.iter().enumerate() {
        let distance = (top - y).abs();
        if distance < best_distance {
            best_distance = distance;
            best = row as i32;
        }
        top += height;
    }
    best
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_default_dock_gives_the_monitor_the_right_column_top_to_bottom() {
        let mut out = DockLayout::default();
        lay_out(&default_dock(), (0.0, 0.0, 1920.0, 1080.0), &mut out);
        let monitor = out
            .seats
            .iter()
            .find(|seat| seat.kind == PaneKind::Preview)
            .expect("a monitor");
        let right = out
            .seats
            .iter()
            .map(|seat| seat.x + seat.width)
            .fold(0.0_f32, f32::max);
        assert!((monitor.x + monitor.width - right).abs() < 0.5, "on the right edge");
        let tallest = out.seats.iter().map(|seat| seat.y + seat.height).fold(0.0_f32, f32::max);
        let top = out.seats.iter().map(|seat| seat.y).fold(f32::MAX, f32::min);
        assert!((monitor.y - top).abs() < 0.5 && (monitor.y + monitor.height - tallest).abs() < 0.5, "the whole height");
        for kind in [PaneKind::Media, PaneKind::Inspector, PaneKind::Timeline, PaneKind::Meters] {
            let seat = out.seats.iter().find(|seat| seat.kind == kind).expect("every pane");
            assert!(seat.x + seat.width <= monitor.x, "{kind:?} left of the monitor");
        }
    }

    #[test]
    fn a_kept_dock_reads_back_as_it_was() {
        let mut dock = default_dock();
        let path = dock.leaf_path(0).expect("a first seat");
        dock.split_leaf(&path, PaneKind::Keyframes, DockSide::Bottom);
        let text = serde_json::to_string(&dock.to_saved()).expect("JSON");
        let read: SavedDock = serde_json::from_str(&text).expect("reads");
        let back = Dock::from_saved(&read).expect("a dock");
        assert_eq!(back.to_saved(), dock.to_saved());
    }

    #[test]
    fn a_damaged_kept_dock_is_refused() {
        let leaf = |pane: &str| Box::new(SavedDock::Leaf { pane: pane.to_owned() });
        let unknown = SavedDock::Split { columns: true, ratio: 0.5, first: leaf("media"), second: leaf("nope") };
        assert!(Dock::from_saved(&unknown).is_none());
        for ratio in [0.0, 1.0, -0.2, f32::NAN] {
            let bad = SavedDock::Split { columns: true, ratio, first: leaf("media"), second: leaf("preview") };
            assert!(Dock::from_saved(&bad).is_none(), "ratio {ratio}");
        }
    }
}
