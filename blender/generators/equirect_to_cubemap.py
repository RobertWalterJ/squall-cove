import cv2, numpy as np
eq = cv2.imread('skybox_golden_hour_4k.png'); H, W = eq.shape[:2]; N = 1024
a = (np.arange(N) + 0.5) / N * 2 - 1
x, y = np.meshgrid(a, -a)
faces = {  # three.js CubeTextureLoader order: px nx py ny pz nz
 'px': ( np.ones_like(x), y, -x), 'nx': (-np.ones_like(x), y, x),
 'py': ( x, np.ones_like(x), -y), 'ny': ( x, -np.ones_like(x), y),
 'pz': ( x, y, np.ones_like(x)),  'nz': (-x, y, -np.ones_like(x)),
}
for k, (dx, dy, dz) in faces.items():
    n = np.sqrt(dx*dx + dy*dy + dz*dz); dx, dy, dz = dx/n, dy/n, dz/n
    u = (np.arctan2(dz, dx) / (2*np.pi) + 0.5) * W
    v = (0.5 - np.arcsin(dy) / np.pi) * H
    cv2.imwrite(f'skybox_pkg/cubemap/{k}.png', cv2.remap(eq, u.astype(np.float32) % W, v.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP))
