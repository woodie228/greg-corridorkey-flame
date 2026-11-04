"""Experimental native-pixel overlapping tile assembly, without inference or I/O.

Independent tile context can change model decisions. This is not equivalent to a
full-frame model profile. Review mattes and motion; use only confirmed empty margins.
"""
import numpy as np


def feather(shape, radius=180):
    height, width = shape
    if min(height, width, radius) < 1:
        raise ValueError('Positive tile dimensions and feather radius required')
    y = np.minimum(np.arange(height)+1, height-np.arange(height))
    x = np.minimum(np.arange(width)+1, width-np.arange(width))
    return (np.minimum(y[:, None], radius)/radius *
            np.minimum(x[None, :], radius)/radius).astype(np.float32)


def assemble(tiles, canvas_hw, active_area, radius=180):
    """Blend (x,y,straight SDR RGB,coverage) tiles in linear premultiplied light.

    Inputs are finite float arrays in [0,1]. Return straight SDR RGB and coverage.
    Only a declared, fully covered active rectangle may contain pixels.
    """
    height,width=canvas_hw
    ax,ay,aw,ah=active_area
    if min(height,width,aw,ah)<1 or min(ax,ay)<0 or ax+aw>width or ay+ah>height:
        raise ValueError('Active area must be inside canvas')
    denominator=np.zeros((height,width),np.float32)
    alpha=np.zeros_like(denominator)
    premult=np.zeros((height,width,3),np.float32)
    for x,y,rgb,a in tiles:
        if rgb.ndim!=3 or rgb.shape[2]!=3 or a.shape!=rgb.shape[:2]:
            raise ValueError('RGB and alpha dimensions must match')
        th,tw=a.shape
        if x<ax or y<ay or x+tw>ax+aw or y+th>ay+ah:
            raise ValueError('Tile must be inside confirmed active area')
        if not all(np.isfinite(v).all() and v.min()>=0 and v.max()<=1 for v in (rgb,a)):
            raise ValueError('Finite SDR RGB and coverage in [0,1] required')
        weight=feather((th,tw),radius)
        region=np.s_[y:y+th,x:x+tw]
        linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
        denominator[region]+=weight
        alpha[region]+=a*weight
        premult[region]+=linear*a[...,None]*weight[...,None]
    if not np.all(denominator[ay:ay+ah,ax:ax+aw]>0):
        raise ValueError('Tiles leave an uncovered active pixel')
    alpha/=np.maximum(denominator,1e-9)
    premult/=np.maximum(denominator[...,None],1e-9)
    linear=premult/np.maximum(alpha[...,None],1e-8)
    rgb=np.where(linear<=.0031308,linear*12.92,1.055*np.maximum(linear,0)**(1/2.4)-.055)
    # Extend only excluded margins for straight-alpha sampling, preserving every
    # active-image RGB/alpha pixel. Coverage outside the rectangle remains zero.
    rgb[ay:ay+ah,:ax]=rgb[ay:ay+ah,ax:ax+1]
    rgb[ay:ay+ah,ax+aw:]=rgb[ay:ay+ah,ax+aw-1:ax+aw]
    rgb[:ay]=rgb[ay:ay+1]
    rgb[ay+ah:]=rgb[ay+ah-1:ay+ah]
    return np.clip(rgb,0,1),np.clip(alpha,0,1)
