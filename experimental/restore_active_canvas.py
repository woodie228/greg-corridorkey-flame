"""Restore cropped active-image passes to their source canvas without erosion.

Only explicitly excluded margins become transparent. Foreground RGB is edge
extended there to avoid black interpolation during later straight-alpha sampling.
"""
from pathlib import Path
import cv2
import numpy as np


def srgb_to_linear(x):
    return np.where(x <= .04045, x / 12.92, ((x + .055) / 1.055) ** 2.4)


def linear_to_srgb(x):
    return np.where(x <= .0031308, x * 12.92, 1.055 * np.maximum(x, .0031308) ** (1 / 2.4) - .055)


def restore(raw, canvas_hw, area):
    raw = Path(raw)
    height, width = canvas_hw
    x, y, active_width, active_height = area
    if min(x,y)<0 or min(active_width,active_height)<1 or x+active_width>width or y+active_height>height:
        raise ValueError('Invalid active area')
    yy,xx=np.indices((height,width))
    checker=np.repeat(np.where(((xx//64+yy//64)%2)==0,.75,.5)[:,:,None],3,axis=2)
    names=sorted(p.name for p in (raw/'fg').iterdir())
    for name in names:
        foreground=cv2.imread(str(raw/'fg'/name),cv2.IMREAD_UNCHANGED)
        matte=cv2.imread(str(raw/'alpha'/name),cv2.IMREAD_UNCHANGED)
        if (foreground is None or matte is None or foreground.dtype!=np.uint16 or matte.dtype!=np.uint16
                or foreground.shape!=(active_height,active_width,3) or matte.shape!=foreground.shape):
            raise ValueError('Unexpected cropped pass: %s'%name)
        fg=cv2.copyMakeBorder(foreground,y,height-y-active_height,x,width-x-active_width,cv2.BORDER_REPLICATE)
        alpha=np.zeros((height,width,3),dtype=np.uint16)
        alpha[y:y+active_height,x:x+active_width]=matte
        # Verify active pixels are preserved exactly; no inward erosion or scaling.
        if not np.array_equal(fg[y:y+active_height,x:x+active_width],foreground):
            raise ValueError('Foreground changed inside active area')
        if not np.array_equal(alpha[y:y+active_height,x:x+active_width],matte):
            raise ValueError('Matte changed inside active area')
        coverage=alpha[:,:,:1].astype(np.float64)/65535
        composite=linear_to_srgb(srgb_to_linear(fg.astype(np.float64)/65535)*coverage+
                                  srgb_to_linear(checker)*(1-coverage))
        composite=np.round(np.clip(composite,0,1)*65535).astype(np.uint16)
        rgba=np.dstack((fg,alpha[:,:,0]))
        for key,image in [('fg',fg),('alpha',alpha),('checker',composite),('cutout',rgba)]:
            if not cv2.imwrite(str(raw/key/name),image):
                raise OSError('Cannot write restored pass')
    return len(names)
