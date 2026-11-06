
const X=(w,W)=>(4000-w)*W/3400;
const path=(d,W,y0,H,lo,hi)=>d.map((p,i)=>(i?'L':'M')+X(p[0],W).toFixed(1)+' '+(y0+H-(p[1]-lo)/(hi-lo)*H).toFixed(1)).join(' ');
const snv=d=>{const v=d.map(p=>p[1]),m=v.reduce((a,b)=>a+b,0)/v.length,s=Math.sqrt(v.reduce((a,b)=>a+(b-m)**2,0)/v.length);return d.map(p=>[p[0],(p[1]-m)/s])};
function grid(W,y0,H,rows){let s='<g stroke="#ececE8">';for(let k=0;k<=rows;k++){const y=y0+H*k/rows;s+=`<line x1="0" y1="${y}" x2="${W}" y2="${y}"/>`}
 for(let k=0;k<7;k++){const x=X(4000-500*k,W);s+=`<line x1="${x}" y1="${y0}" x2="${x}" y2="${y0+H}"/>`}return s+'</g>'}
function xl(W,y){let s='<g font-family="IBM Plex Mono,monospace" font-size="12" fill="#4a5159">';for(let k=0;k<7;k++)s+=`<text x="${X(4000-500*k,W)}" y="${y}" text-anchor="middle">${4000-500*k}</text>`;return s+'</g>'}
function yl(y0,H,lo,hi,ticks,fmt){return '<g font-family="IBM Plex Mono,monospace" font-size="12" fill="#4a5159">'+ticks.map(v=>`<text x="-10" y="${(y0+H-(v-lo)/(hi-lo)*H+4).toFixed(0)}" text-anchor="end">${fmt(v)}</text>`).join('')+'</g>'}
