import { useState, useMemo } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

const T = {
  bg:"#04090f",card:"#080f1c",hover:"#0d1628",border:"#142030",borderHi:"#1e3050",
  gold:"#e8a020",goldBg:"#2a1e08",teal:"#00c8a0",tealBg:"#003828",
  text:"#c8d8f0",muted:"#4a6080",dim:"#2a3850",
};

const STOCKS = [
  {code:"8306",name:"三菱UFJ FG",     sector:"銀行業",      yield_:4.12,pbr:0.76,per:11.8,roe:7.2, equity:5.8, years:8, fin:true },
  {code:"8316",name:"三井住友FG",      sector:"銀行業",      yield_:4.56,pbr:0.69,per:10.2,roe:7.8, equity:4.9, years:11,fin:true },
  {code:"8058",name:"三菱商事",         sector:"卸売業",      yield_:3.98,pbr:0.91,per:9.8, roe:10.2,equity:33.5,years:5, fin:false},
  {code:"5401",name:"日本製鉄",         sector:"鉄鋼業",      yield_:5.21,pbr:0.62,per:7.1, roe:9.2, equity:42.1,years:3, fin:false},
  {code:"8053",name:"住友商事",         sector:"卸売業",      yield_:4.45,pbr:0.74,per:7.8, roe:10.5,equity:35.2,years:6, fin:false},
  {code:"8591",name:"オリックス",       sector:"その他金融業",yield_:4.18,pbr:0.87,per:9.8, roe:9.2, equity:21.5,years:9, fin:true },
  {code:"4502",name:"武田薬品工業",     sector:"医薬品",      yield_:4.82,pbr:0.92,per:31.2,roe:3.1, equity:40.8,years:15,fin:false},
  {code:"1605",name:"INPEX",           sector:"鉱業",        yield_:4.35,pbr:0.58,per:7.5, roe:8.5, equity:52.1,years:5, fin:false},
  {code:"3407",name:"旭化成",           sector:"化学",        yield_:3.88,pbr:0.82,per:17.8,roe:4.8, equity:48.5,years:7, fin:false},
  {code:"8002",name:"丸紅",             sector:"卸売業",      yield_:4.02,pbr:0.78,per:8.2, roe:10.8,equity:28.5,years:5, fin:false},
  {code:"5802",name:"住友電工",         sector:"非鉄金属",    yield_:3.92,pbr:0.68,per:12.5,roe:5.8, equity:43.2,years:6, fin:false},
  {code:"7751",name:"キヤノン",         sector:"電気機器",    yield_:4.28,pbr:1.01,per:14.8,roe:7.2, equity:58.2,years:18,fin:false},
  {code:"9432",name:"NTT",             sector:"情報・通信業",yield_:3.78,pbr:1.52,per:12.1,roe:13.5,equity:21.8,years:13,fin:false},
  {code:"8766",name:"東京海上HD",       sector:"保険業",      yield_:3.65,pbr:1.48,per:13.5,roe:12.1,equity:18.2,years:14,fin:true },
  {code:"9433",name:"KDDI",            sector:"情報・通信業",yield_:3.52,pbr:2.01,per:14.2,roe:14.8,equity:38.2,years:22,fin:false},
  {code:"8001",name:"伊藤忠商事",       sector:"卸売業",      yield_:3.75,pbr:1.21,per:9.2, roe:14.1,equity:31.2,years:7, fin:false},
  {code:"5411",name:"JFEホールディングス",sector:"鉄鋼業",   yield_:4.95,pbr:0.55,per:6.8, roe:8.8, equity:38.5,years:3, fin:false},
  {code:"8830",name:"住友不動産",       sector:"不動産業",    yield_:3.62,pbr:0.82,per:10.5,roe:8.2, equity:22.4,years:5, fin:false},
];

const SC = {
  "銀行業":"#4488ff","卸売業":"#e8a020","鉄鋼業":"#909090","その他金融業":"#7799dd",
  "医薬品":"#44dd88","鉱業":"#bb9944","化学":"#dd6644","非鉄金属":"#bbaa44",
  "電気機器":"#44aadd","情報・通信業":"#44cc44","保険業":"#dd44aa","不動産業":"#aa66cc",
};

function calcScore(s){
  return Math.round(
    Math.min(s.yield_/6*30,30)+Math.max(0,(1.5-s.pbr)/1.5*25)+
    Math.min(s.roe/15*20,20)+Math.min(s.years/20*15,15)+
    (s.fin?10:Math.min(s.equity/60*10,10))
  );
}

function Slider({label,value,onChange,min,max,step,unit}){
  return(
    <div style={{marginBottom:18}}>
      <div style={{display:"flex",justifyContent:"space-between",marginBottom:5}}>
        <span style={{color:T.muted,fontSize:10,textTransform:"uppercase",letterSpacing:.8}}>{label}</span>
        <span style={{color:T.gold,fontSize:12,fontFamily:"monospace",fontWeight:700}}>{value}{unit}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={e=>onChange(parseFloat(e.target.value))}
        style={{width:"100%",accentColor:T.gold,cursor:"pointer"}}/>
      <div style={{display:"flex",justifyContent:"space-between",marginTop:3}}>
        <span style={{color:T.dim,fontSize:9}}>{min}{unit}</span>
        <span style={{color:T.dim,fontSize:9}}>{max}{unit}</span>
      </div>
    </div>
  );
}

export default function App(){
  const [f,setF]=useState({minYield:3.5,maxPBR:1.0,minROE:5.0,minEquity:25,minYears:3});
  const [sort,setSort]=useState({field:"score",dir:"desc"});
  const [hov,setHov]=useState(null);
  const [sec,setSec]=useState(null);
  const set=k=>v=>setF(p=>({...p,[k]:v}));

  const results=useMemo(()=>
    STOCKS.filter(s=>
      s.yield_>=f.minYield&&s.pbr<=f.maxPBR&&s.roe>=f.minROE&&
      (s.fin||s.equity>=f.minEquity)&&s.years>=f.minYears&&
      (!sec||s.sector===sec)
    ).map(s=>({...s,score:calcScore(s)}))
    .sort((a,b)=>sort.dir==="desc"?b[sort.field]-a[sort.field]:a[sort.field]-b[sort.field])
  ,[f,sort,sec]);

  const secData=useMemo(()=>{
    const m={};results.forEach(s=>{m[s.sector]=(m[s.sector]||0)+1;});
    return Object.entries(m).map(([name,count])=>({name,count})).sort((a,b)=>b.count-a.count);
  },[results]);

  const avg=k=>results.length?(results.reduce((s,r)=>s+r[k],0)/results.length):0;
  const hs=field=>setSort(s=>({field,dir:s.field===field?(s.dir==="desc"?"asc":"desc"):"desc"}));

  const Th=({field,label,al="right"})=>(
    <th onClick={()=>hs(field)} style={{
      padding:"10px 12px",textAlign:al,cursor:"pointer",userSelect:"none",whiteSpace:"nowrap",
      position:"sticky",top:0,zIndex:1,
      color:sort.field===field?T.gold:T.muted,fontSize:10,textTransform:"uppercase",letterSpacing:.8,
      borderBottom:`1px solid ${T.border}`,background:T.card,fontWeight:sort.field===field?700:400,
    }}>{label}{sort.field===field?(sort.dir==="desc"?" ▼":" ▲"):""}</th>
  );

  const sectors=[...new Set(STOCKS.map(s=>s.sector))];

  return(
    <div style={{background:T.bg,minHeight:"100vh",color:T.text,fontFamily:"system-ui,-apple-system,sans-serif",fontSize:13}}>
      <div style={{background:T.card,borderBottom:`1px solid ${T.border}`,padding:"10px 20px",display:"flex",alignItems:"center",justifyContent:"space-between"}}>
        <div style={{display:"flex",alignItems:"center",gap:12}}>
          <div style={{width:34,height:34,background:T.gold,borderRadius:7,display:"flex",alignItems:"center",justifyContent:"center",flexShrink:0}}>
            <span style={{color:"#000",fontWeight:900,fontSize:18,fontFamily:"monospace"}}>¥</span>
          </div>
          <div>
            <div style={{fontWeight:700,fontSize:15}}>StockScreener JP <span style={{color:T.muted,fontSize:11,fontWeight:400}}>— 高配当・低PBR・安定株</span></div>
            <div style={{color:T.muted,fontSize:10,marginTop:2}}>データソース: J-Quants API (JPX公式)　·　毎週月曜 07:00 JST 自動更新 (GitHub Actions)</div>
          </div>
        </div>
        <div style={{display:"flex",alignItems:"center",gap:10}}>
          <div style={{display:"flex",alignItems:"center",gap:6}}>
            <div style={{width:6,height:6,borderRadius:"50%",background:T.teal,boxShadow:`0 0 8px ${T.teal}`}}/>
            <span style={{color:T.muted,fontSize:11}}>最終更新: 2026/04/14 07:00 JST</span>
          </div>
          <span style={{background:T.tealBg,border:`1px solid ${T.teal}44`,color:T.teal,fontSize:10,padding:"3px 9px",borderRadius:3}}>⚡ デモデータ</span>
        </div>
      </div>

      <div style={{display:"flex"}}>
        <div style={{width:215,background:T.card,borderRight:`1px solid ${T.border}`,padding:18,flexShrink:0,overflowY:"auto",minHeight:"calc(100vh - 57px)",boxSizing:"border-box"}}>
          <div style={{color:T.gold,fontSize:10,fontWeight:700,letterSpacing:1.5,textTransform:"uppercase",marginBottom:16,paddingBottom:10,borderBottom:`1px solid ${T.border}`}}>スクリーニング条件</div>
          <Slider label="配当利回り 最低"  value={f.minYield}  onChange={set("minYield")}  min={1}  max={7}   step={.1} unit="%"/>
          <Slider label="PBR 上限"         value={f.maxPBR}    onChange={set("maxPBR")}    min={.3} max={2.0} step={.1} unit="倍"/>
          <Slider label="ROE 最低"         value={f.minROE}    onChange={set("minROE")}    min={0}  max={20}  step={.5} unit="%"/>
          <Slider label="自己資本比率 最低" value={f.minEquity} onChange={set("minEquity")} min={10} max={60}  step={5}  unit="%"/>
          <Slider label="連続配当年数 最低" value={f.minYears}  onChange={set("minYears")}  min={1}  max={20}  step={1}  unit="年"/>
          <div style={{background:"#0a1c0f",border:`1px solid #1c3820`,borderRadius:4,padding:"8px 10px",fontSize:10,color:"#48a060",lineHeight:1.7,marginBottom:20}}>
            ⚠ 銀行・保険・金融株は<br/>自己資本比率基準を自動除外
          </div>
          <div style={{paddingTop:14,borderTop:`1px solid ${T.border}`}}>
            <div style={{color:T.muted,fontSize:10,textTransform:"uppercase",letterSpacing:1,marginBottom:10}}>セクター絞り込み</div>
            {[null,...sectors].map(s=>(
              <button key={s||"all"} onClick={()=>setSec(s===sec?null:s)}
                style={{width:"100%",padding:"5px 10px",marginBottom:3,textAlign:"left",
                  background:sec===s?T.goldBg:"transparent",
                  border:`1px solid ${sec===s?T.gold+"88":T.border}`,
                  borderRadius:3,color:sec===s?T.gold:T.muted,cursor:"pointer",fontSize:11}}>
                {s?<span><span style={{display:"inline-block",width:6,height:6,borderRadius:"50%",background:SC[s]||T.muted,marginRight:6}}/>{s}</span>:"すべて"}
              </button>
            ))}
          </div>
        </div>

        <div style={{flex:1,display:"flex",flexDirection:"column",overflow:"hidden"}}>
          <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:1,background:T.border}}>
            {[
              {label:"ヒット銘柄数",  val:results.length,          unit:"銘柄",sub:`全${STOCKS.length}銘柄中`,c:T.gold},
              {label:"平均配当利回り",val:avg("yield_").toFixed(2), unit:"%",  sub:"スクリーニング平均",      c:T.teal},
              {label:"平均 PBR",      val:avg("pbr").toFixed(2),    unit:"倍", sub:"スクリーニング平均",      c:T.teal},
              {label:"平均 ROE",      val:avg("roe").toFixed(1),    unit:"%",  sub:"スクリーニング平均",      c:T.teal},
            ].map((c,i)=>(
              <div key={i} style={{background:T.card,padding:"14px 18px"}}>
                <div style={{color:T.muted,fontSize:10,textTransform:"uppercase",letterSpacing:.8,marginBottom:5}}>{c.label}</div>
                <div style={{display:"flex",alignItems:"baseline",gap:3}}>
                  <span style={{color:c.c,fontSize:26,fontWeight:700,fontFamily:"monospace",lineHeight:1}}>{c.val}</span>
                  <span style={{color:c.c+"88",fontSize:13}}>{c.unit}</span>
                </div>
                <div style={{color:T.dim,fontSize:10,marginTop:4}}>{c.sub}</div>
              </div>
            ))}
          </div>

          <div style={{flex:1,overflowX:"auto",overflowY:"auto"}}>
            <table style={{width:"100%",borderCollapse:"collapse"}}>
              <thead>
                <tr>
                  <Th field="code"   label="コード / 銘柄名" al="left"/>
                  <Th field="sector" label="セクター"         al="left"/>
                  <Th field="yield_" label="配当利回り"/>
                  <Th field="pbr"    label="PBR"/>
                  <Th field="per"    label="PER"/>
                  <Th field="roe"    label="ROE"/>
                  <Th field="equity" label="自己資本比率"/>
                  <Th field="years"  label="連続配当"/>
                  <Th field="score"  label="スコア"/>
                </tr>
              </thead>
              <tbody>
                {results.map((s,i)=>(
                  <tr key={s.code} onMouseEnter={()=>setHov(s.code)} onMouseLeave={()=>setHov(null)}
                    style={{background:hov===s.code?T.hover:(i%2===0?"#060b14":T.bg),borderBottom:`1px solid ${T.border}`}}>
                    <td style={{padding:"11px 12px"}}>
                      <div style={{display:"flex",alignItems:"center",gap:8}}>
                        <span style={{color:T.gold,fontFamily:"monospace",fontSize:12,fontWeight:700,minWidth:38}}>{s.code}</span>
                        <span>{s.name}</span>
                        {s.fin&&<span style={{background:"#142030",border:`1px solid #1e3050`,color:"#5580aa",fontSize:9,padding:"1px 5px",borderRadius:2}}>金融</span>}
                      </div>
                    </td>
                    <td style={{padding:"11px 12px"}}>
                      <span style={{color:SC[s.sector]||T.muted,background:T.border,fontSize:11,padding:"2px 7px",borderRadius:2}}>{s.sector}</span>
                    </td>
                    <td style={{padding:"11px 12px",textAlign:"right",fontFamily:"monospace",fontWeight:700,color:s.yield_>=4.5?T.teal:s.yield_>=3.5?T.text:T.muted}}>{s.yield_.toFixed(2)}%</td>
                    <td style={{padding:"11px 12px",textAlign:"right",fontFamily:"monospace",color:s.pbr<=.7?T.teal:s.pbr<=1?T.text:T.muted}}>{s.pbr.toFixed(2)}x</td>
                    <td style={{padding:"11px 12px",textAlign:"right",fontFamily:"monospace",color:T.muted}}>{s.per.toFixed(1)}x</td>
                    <td style={{padding:"11px 12px",textAlign:"right",fontFamily:"monospace",color:s.roe>=10?T.teal:s.roe>=5?T.text:T.muted}}>{s.roe.toFixed(1)}%</td>
                    <td style={{padding:"11px 12px",textAlign:"right",fontFamily:"monospace"}}>
                      {s.fin?<span style={{color:T.dim,fontSize:11}}>金融基準</span>:<span style={{color:s.equity>=40?T.teal:T.text}}>{s.equity.toFixed(1)}%</span>}
                    </td>
                    <td style={{padding:"11px 12px",textAlign:"right",fontFamily:"monospace",color:s.years>=10?T.teal:T.text}}>{s.years}年</td>
                    <td style={{padding:"11px 12px",textAlign:"right"}}>
                      <div style={{display:"inline-flex",alignItems:"center",gap:8}}>
                        <div style={{width:44,height:3,background:T.dim,borderRadius:2}}>
                          <div style={{width:`${s.score}%`,height:"100%",borderRadius:2,background:s.score>=70?T.teal:s.score>=50?T.gold:T.muted}}/>
                        </div>
                        <span style={{fontFamily:"monospace",fontWeight:700,minWidth:22,textAlign:"right",color:s.score>=70?T.teal:s.score>=50?T.gold:T.muted}}>{s.score}</span>
                      </div>
                    </td>
                  </tr>
                ))}
                {results.length===0&&(
                  <tr><td colSpan={9} style={{padding:60,textAlign:"center",color:T.muted}}>条件に合う銘柄がありません。フィルターを緩めてください。</td></tr>
                )}
              </tbody>
            </table>
          </div>

          {secData.length>0&&(
            <div style={{background:T.card,borderTop:`1px solid ${T.border}`,padding:"14px 20px"}}>
              <div style={{color:T.muted,fontSize:10,textTransform:"uppercase",letterSpacing:1,marginBottom:12}}>セクター分布</div>
              <ResponsiveContainer width="100%" height={90}>
                <BarChart data={secData} margin={{top:0,right:10,bottom:0,left:-15}}>
                  <XAxis dataKey="name" tick={{fill:T.muted,fontSize:9}} axisLine={false} tickLine={false}/>
                  <YAxis tick={{fill:T.muted,fontSize:9}} axisLine={false} tickLine={false} allowDecimals={false}/>
                  <Tooltip contentStyle={{background:T.card,border:`1px solid ${T.borderHi}`,borderRadius:4,fontSize:11}}
                    labelStyle={{color:T.text}} itemStyle={{color:T.gold}} formatter={v=>[v,"銘柄数"]}/>
                  <Bar dataKey="count" radius={[2,2,0,0]}>
                    {secData.map((e,i)=><Cell key={i} fill={SC[e.name]||T.gold}/>)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
