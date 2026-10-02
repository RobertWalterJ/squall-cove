import cv2, numpy as np, sys
def fix(img, linear, r0f=476/1024):
    img = img.astype(np.float32); H, W = img.shape[:2]; h0 = H // 2
    r0 = int(round(r0f * H))
    ref = img[r0]
    pad = np.concatenate([ref[-W//4:], ref, ref[:W//4]])
    refb = cv2.GaussianBlur(pad[None], (0, 0), sigmaX=W / 40)[0][W//4: W//4 + W]
    mean = ref.mean(axis=0)
    out = img.copy()
    for r in range(r0 + 1, H):
        if r <= h0:
            a = (r - r0) / (h0 - r0)
            out[r] = img[r] * (1 - a) + refb * a if r < r0 + 6 else refb * (1 - 0.05 * a)
            if r < r0 + 6: out[r] = img[r] * (1 - (r - r0) / 6) + refb * ((r - r0) / 6)
        else:
            t = (r - h0) / (H - h0)
            f = 0.95 - (0.95 - (0.28 if linear else 0.5)) * (1 - (1 - t) ** 2.5)
            m = min(1.0, t * 2.5)
            out[r] = (refb * (1 - m) + mean * m) * f
    return out
hdr = cv2.imread(sys.argv[1], cv2.IMREAD_UNCHANGED)
cv2.imwrite(sys.argv[3], fix(hdr, True))
png = cv2.imread(sys.argv[2])
cv2.imwrite(sys.argv[4], np.clip(fix(png, False), 0, 255).astype(np.uint8))
