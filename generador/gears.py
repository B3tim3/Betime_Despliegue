import math
K=9.0
def profile(N, phase_deg):
    """Puntos (x,y) de un engranaje de N dientes. k=9: paso r=N*k/2, raíz=paso-k, punta=paso+0.8k."""
    rp=N*K/2; root=rp-K; tip=rp+0.8*K
    p=360.0/N
    pts=[]
    for i in range(N):
        c=phase_deg+i*p
        for (r,off) in ((root,-0.30),(tip,-0.14),(tip,0.14),(root,0.30)):
            a=math.radians(c+off*p); pts.append((r*math.cos(a), r*math.sin(a),r))
    return pts,root,tip,rp
def path(N,phase):
    pts,root,tip,rp=profile(N,phase)
    d=[]
    for i,(x,y,r) in enumerate(pts):
        if i==0: d.append(f"M{x:.2f},{y:.2f}")
        else:
            # entre diente y diente (raíz->raíz) se usa un arco; el resto son líneas
            if i%4==0: d.append(f"A{root:.2f},{root:.2f} 0 0 1 {x:.2f},{y:.2f}")
            else: d.append(f"L{x:.2f},{y:.2f}")
    d.append(f"A{root:.2f},{root:.2f} 0 0 1 {pts[0][0]:.2f},{pts[0][1]:.2f}Z")
    return "".join(d),root,tip
if __name__=="__main__":
    # verificación de engrane: giramos el central α y los chicos -1.6α; el solape debe ser ~0
    from PIL import Image, ImageDraw
    import itertools
    S=4; W=360*S
    def poly(N,phase,cx,cy,rot):
        pts,_,_,_=profile(N,phase+rot)
        return [((cx+x)*S,(cy+y)*S) for x,y,_ in pts]
    sats=[(225,27),(315,9),(135,9),(45,27)]
    worst=0
    for alpha in range(0,360,3):
        for th,ph in sats:
            cx=180+117*math.cos(math.radians(th)); cy=180+117*math.sin(math.radians(th))
            a=Image.new("1",(W,W),0); b=Image.new("1",(W,W),0)
            ImageDraw.Draw(a).polygon(poly(16,0,180,180,alpha),fill=1)
            ImageDraw.Draw(b).polygon(poly(10,ph,cx,cy,-1.6*alpha),fill=1)
            import numpy as np
            ov=(np.array(a)&np.array(b)).sum()/(S*S)
            worst=max(worst,ov)
    print("solape máximo (u²):",round(worst,2),"| área de un diente ≈",round(0.4*math.pi*2*72/16*16.2/2,1))
