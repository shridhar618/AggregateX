'use strict';
let original=null,sourceWidth=0,sourceHeight=0;
// Deterministic edge-clamped separable box blur. Alpha is retained, never invented.
function box(input,w,h,r){
 if(!r)return input;
 const temp=new Uint8ClampedArray(input.length),out=new Uint8ClampedArray(input.length),n=2*r+1;
 for(let y=0;y<h;y++)for(let c=0;c<3;c++){
  let sum=0;for(let x=-r;x<=r;x++)sum+=input[(y*w+Math.max(0,Math.min(w-1,x)))*4+c];
  for(let x=0;x<w;x++){temp[(y*w+x)*4+c]=sum/n;sum+=input[(y*w+Math.min(w-1,x+r+1))*4+c]-input[(y*w+Math.max(0,x-r))*4+c];}
 }
 for(let x=0;x<w;x++)for(let c=0;c<3;c++){
  let sum=0;for(let y=-r;y<=r;y++)sum+=temp[(Math.max(0,Math.min(h-1,y))*w+x)*4+c];
  for(let y=0;y<h;y++){out[(y*w+x)*4+c]=sum/n;sum+=temp[(Math.min(h-1,y+r+1)*w+x)*4+c]-temp[(Math.max(0,y-r)*w+x)*4+c];}
 }
 for(let i=3;i<input.length;i+=4)out[i]=input[i];return out;
}
self.onmessage=async({data:m})=>{
 if(m.type==='source'){original=new Uint8ClampedArray(m.buffer);sourceWidth=m.width;sourceHeight=m.height;return;}
 if(m.type!=='render'||!original)return;
 try{
  const a=m.adjustments,w=sourceWidth,h=sourceHeight;
  const ow=Math.max(32,Math.round(w*a.resize/100)),oh=Math.max(32,Math.round(h*a.resize/100));
  if(ow>8192||oh>8192||ow*oh>16000000)throw Error('Resize exceeds 8192 pixels per side or 16 megapixels.');
  let pixels=new Uint8ClampedArray(original);
  const neutral=a.brightness===0&&a.contrast===0&&a.exposure===0&&a.gamma===1&&a.highlights===0&&a.shadows===0&&a.saturation===100&&a.temperature===0&&!a.grayscale&&!a.invert;
  if(!neutral){
   const exposure=2**a.exposure,contrast=(100+a.contrast)/(100-a.contrast),saturation=a.saturation/100;
   for(let i=0;i<pixels.length;i+=4){
    let r=original[i]/255,g=original[i+1]/255,b=original[i+2]/255;
    const l=.2126*r+.7152*g+.0722*b,offset=(a.shadows/100*(1-l)**2+a.highlights/100*l*l)*.35;
    r=Math.max(0,r*exposure+offset);g=Math.max(0,g*exposure+offset);b=Math.max(0,b*exposure+offset);
    r=r**(1/a.gamma);g=g**(1/a.gamma);b=b**(1/a.gamma);
    r=(r-.5)*contrast+.5+a.brightness/100;g=(g-.5)*contrast+.5+a.brightness/100;b=(b-.5)*contrast+.5+a.brightness/100;
    r+=a.temperature/300;b-=a.temperature/300;
    const gray=.2126*r+.7152*g+.0722*b;
    r=gray+(r-gray)*saturation;g=gray+(g-gray)*saturation;b=gray+(b-gray)*saturation;
    if(a.grayscale)r=g=b=.2126*r+.7152*g+.0722*b;
    if(a.invert){r=1-r;g=1-g;b=1-b;}
    pixels[i]=r*255;pixels[i+1]=g*255;pixels[i+2]=b*255;
   }
  }
  if(a.smoothing){const smooth=box(pixels,w,h,1),blend=a.smoothing/100;for(let i=0;i<pixels.length;i++)if(i%4!==3)pixels[i]=pixels[i]*(1-blend)+smooth[i]*blend;}
  if(a.blur)pixels=box(pixels,w,h,a.blur);
  if(a.sharpen){const smooth=box(pixels,w,h,1),strength=a.sharpen/100;for(let i=0;i<pixels.length;i++)if(i%4!==3)pixels[i]=pixels[i]+(pixels[i]-smooth[i])*strength;}
  let canvas=new OffscreenCanvas(w,h);canvas.getContext('2d').putImageData(new ImageData(pixels,w,h),0,0);
  if(ow!==w||oh!==h){const resized=new OffscreenCanvas(ow,oh),ctx=resized.getContext('2d');ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';ctx.drawImage(canvas,0,0,ow,oh);canvas=resized;}
  const blob=await canvas.convertToBlob({type:'image/png'});self.postMessage({type:'result',id:m.id,width:ow,height:oh,blob});
 }catch(error){self.postMessage({type:'error',id:m.id,message:error.message});}
};
