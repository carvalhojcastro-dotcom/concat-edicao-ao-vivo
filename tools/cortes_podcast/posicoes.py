import sys, subprocess, numpy as np
sys.path.insert(0, sys.argv[0].rsplit('/',1)[0]); from rostos import Rostos
src = sys.argv[1]; R = Rostos(1280, 720)
for t in [float(x) for x in sys.argv[2:]]:
    raw = subprocess.run(["ffmpeg","-v","error","-ss",str(t),"-i",src,"-frames:v","1","-vf","scale=1280:720","-f","rawvideo","-pix_fmt","rgb24","-"],capture_output=True).stdout
    f = np.frombuffer(raw,np.uint8).reshape(720,1280,3)
    lay = "host" if f[0:180,0:384].reshape(-1,3).mean(0)[0] > 120 else "guest"
    print(t, lay, sorted((round(a,3),round(b,3),round(c,3),round(d,3)) for a,b,c,d in R(f)))
