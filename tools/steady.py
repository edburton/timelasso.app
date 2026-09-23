# Holds the city still in a clip shot from a mount that drifts (it warps as
# the sun heats it). The skyline band, rows 55-95% of the frame, is the only
# part where nothing moves but the camera: each frame's offset against the
# first is found there by phase correlation of vertical gradients, and each
# frame is then cropped at that offset. Every frame loses the widest drift,
# keeping 16:9; the drift itself is what is left out.
#
#   python3 tools/steady.py clip.MOV steady.mp4
import sys, json, subprocess, numpy as np

src, dst = sys.argv[1:3]
probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
    "stream=width,height:stream_side_data=rotation", "-of", "json", src], capture_output=True).stdout)["streams"][0]
W, H = probe["width"], probe["height"]
if abs(next((d.get("rotation", 0) for d in probe.get("side_data_list", [])), 0)) == 90: W, H = H, W

# Measure at a quarter size; the sub-pixel peak brings it back under a pixel.
w4, h4 = W // 4, H // 4
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vf", f"fps=30,scale={w4}:{h4},format=gray",
    "-f", "rawvideo", "-"], capture_output=True).stdout
band = np.frombuffer(raw, np.uint8).reshape(-1, h4, w4).astype(np.float32)[:, int(h4*.55):int(h4*.95), :]
g = np.diff(band, axis=1)
win = np.hanning(g.shape[1])[:, None] * np.hanning(g.shape[2])[None, :]
F0 = np.fft.fft2((g[0] - g[0].mean()) * win)

def peak(a, k):
    l, m, r = a[(k-1) % len(a)], a[k], a[(k+1) % len(a)]
    d = l - 2*m + r
    return k + (0.5*(l - r)/d if d else 0)

shift = []
for f in g:
    R = F0 * np.conj(np.fft.fft2((f - f.mean()) * win))
    c = np.fft.ifft2(R / (np.abs(R) + 1e-9)).real
    y, x = np.unravel_index(c.argmax(), c.shape)
    dy, dx = peak(c[:, x], y), peak(c[y, :], x)
    if dy > c.shape[0]/2: dy -= c.shape[0]
    if dx > c.shape[1]/2: dx -= c.shape[1]
    shift.append((-dx * W / w4, -dy * H / h4))
s = np.round(np.array(shift)).astype(int)
ox, oy = s[:, 0] - s[:, 0].min(), s[:, 1] - s[:, 1].min()
h = (H - oy.max()) // 2 * 2
w = int(h * 16 / 9) // 2 * 2
mx = (W - w - ox.max()) // 2
assert mx >= 0, "drifted too far sideways to keep 16:9"
print(f"drift {ox.max()} x {oy.max()} px, cropping to {w}x{h}")

dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-vf", "fps=30", "-pix_fmt", "rgb24",
    "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
    "-r", "30", "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", "-pix_fmt", "yuv420p", dst],
    stdin=subprocess.PIPE)
n, size = 0, W * H * 3
while (b := dec.stdout.read(size)) and len(b) == size:
    i = min(n, len(s) - 1)
    f = np.frombuffer(b, np.uint8).reshape(H, W, 3)
    enc.stdin.write(np.ascontiguousarray(f[oy[i]:oy[i]+h, mx+ox[i]:mx+ox[i]+w]).tobytes())
    n += 1
enc.stdin.close()
enc.wait()
