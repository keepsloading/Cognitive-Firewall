(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.RustmeterScorer = factory();
  }
}(typeof self !== 'undefined' ? self : this, function () {
  const ENGINE_VERSION = 'rustmeter-local-rules-1.0';
  const SIGNALS = [
    { category: 'attention_capture', weight: 14, reason: 'Curiosity-gap wording captures attention before substance.', pattern: /\b(everyone is talking about|what happened next|what happens next|the truth about|this is why|the reason why)\b/gi },
    { category: 'clickbait', weight: 15, reason: 'Clickbait wording pushes curiosity pressure.', pattern: /\b(you won't believe|you will not believe|shocking|secret|hidden|mind-blowing|before you)\b/gi },
    { category: 'emotional_pressure', weight: 13, reason: 'Identity or guilt pressure pushes emotional compliance.', pattern: /\b(if you care|don't stay silent|do not stay silent|wake up|open your eyes|only idiots)\b/gi },
    { category: 'fear_appeal', weight: 13, reason: 'Threat-oriented wording increases fear pressure.', pattern: /\b(warning|danger|collapse|crisis|deadly|panic|catastrophe)\b/gi },
    { category: 'outrage_amplification', weight: 13, reason: 'Outrage-first wording primes anger over context.', pattern: /\b(furious|outraged|slammed|destroyed|humiliated|betrayed|scandal)\b/gi },
    { category: 'false_urgency', weight: 12, reason: 'Urgency cues pressure immediate reaction.', pattern: /\b(act now|right now|before it's too late|before it is too late|last chance|must see|don't miss|do not miss)\b/gi },
    { category: 'loaded_language', weight: 11, reason: 'Loaded language can bias interpretation.', pattern: /\b(corrupt|evil|traitors|idiots|shameless|disgusting|lies)\b/gi },
    { category: 'enemy_construction', weight: 13, reason: 'Us-versus-them framing constructs enemy targets.', pattern: /\b(traitors|enemies of the people|the elites|they don't want you to know|they do not want you to know|they are destroying us|corrupt media)\b/gi },
    { category: 'polarization', weight: 12, reason: 'Polarizing language frames rigid camps.', pattern: /\b(us vs them|real [a-z]+|anti-national|woke mob|leftists|right-wingers|pick a side)\b/gi },
    { category: 'certainty_inflation', weight: 10, reason: 'Absolute certainty removes nuance.', pattern: /\b(always|never|everyone knows|nobody talks about|proves|proof that|undeniable|guaranteed|without question|no doubt)\b/gi },
    { category: 'source_obscurity', weight: 10, reason: 'Vague sourcing weakens verifiability.', pattern: /\b(experts say|sources say|people are saying|some say|many believe|it is believed|reportedly|allegedly|rumor has it)\b/gi },
    { category: 'social_proof_pressure', weight: 11, reason: 'Social-proof cues pressure conformity.', pattern: /\b(everyone is talking about|millions agree|people are waking up|the whole internet|viral|many believe)\b/gi },
    { category: 'engagement_bait', weight: 10, reason: 'Engagement bait prompts interaction over understanding.', pattern: /\b(like and share|comment below|tag someone|subscribe now|watch till the end|watch until the end|share before they delete this)\b/gi },
    { category: 'call_to_action_pressure', weight: 10, reason: 'Call-to-action pressure pushes immediate action.', pattern: /\b(share this if|send this to everyone|join now|don't stay silent|do not stay silent|boycott|act now|wake up)\b/gi }
  ];
  const CATEGORY_KEYS = [...new Set(SIGNALS.map(s=>s.category))];
  function cleanText(v){return (v||'').replace(/\s+/g,' ').trim();}
  function clamp(v,min=0,max=100){return Math.max(min,Math.min(max,v));}
  function tokenize(t){return cleanText(t).match(/\b[\w'-]+\b/g)||[];}
  function toTitle(k){return k.split('_').map(x=>x[0].toUpperCase()+x.slice(1)).join(' ');}
  function scoreContent(content,requestId=''){
    const headline=cleanText(content.headline); const body=cleanText([content.byline,content.snippet].filter(Boolean).join(' ')); const all=cleanText([headline,body].join(' '));
    const scores=Object.fromEntries(CATEGORY_KEYS.map(k=>[k,0])); const evidence=[];
    for(const s of SIGNALS){for(const scope of [{name:'headline',text:headline,m:1.45},{name:'body',text:body,m:1.0}]){s.pattern.lastIndex=0;let m;while((m=s.pattern.exec(scope.text))){const p=cleanText(m[0]);const a=s.weight*scope.m;scores[s.category]+=a;evidence.push({signal:p,reason:s.reason,category:s.category,location:scope.name,weight:a});}}}
    const ex=(all.match(/!/g)||[]).length, q=(all.match(/\?/g)||[]).length, caps=(all.match(/\b[A-Z]{3,}\b/g)||[]).length;
    if(ex||q){const p=Math.min(14,ex*3+Math.max(0,q-1)*2);scores.attention_capture+=p;scores.false_urgency+=p*0.5;}
    if(caps){const p=Math.min(14,caps*3);scores.false_urgency+=p;scores.loaded_language+=p*0.4;}
    const wc=Math.max(content.word_count||tokenize(all).length,1); const norm={};
    for(const [k,v] of Object.entries(scores)){norm[k]=clamp(Math.round((v*5.8)/Math.max(1.15,Math.log10(Math.max(wc,15)))))}
    const attention=clamp(Math.round(norm.attention_capture*0.34+norm.clickbait*0.30+norm.engagement_bait*0.20+norm.social_proof_pressure*0.16));
    const emotion=clamp(Math.round(norm.emotional_pressure*0.32+norm.fear_appeal*0.24+norm.outrage_amplification*0.24+norm.false_urgency*0.20));
    const framing=clamp(Math.round(norm.loaded_language*0.26+norm.enemy_construction*0.30+norm.polarization*0.24+norm.certainty_inflation*0.20));
    const source=clamp(Math.round(norm.source_obscurity*0.74+norm.certainty_inflation*0.14+norm.social_proof_pressure*0.12));
    const rust=clamp(Math.round(attention*0.28+emotion*0.27+framing*0.27+source*0.18));
    const sorted=evidence.sort((a,b)=>b.weight-a.weight).filter((it,idx,arr)=>arr.findIndex(o=>o.signal.toLowerCase()===it.signal.toLowerCase()&&o.category===it.category)===idx);
    const top=(sorted.slice(0,5).map(({signal,reason,category,location})=>({signal,reason,category,location})));
    const tactics=Object.entries(norm).filter(([,v])=>v>=28).sort((a,b)=>b[1]-a[1]).map(([k])=>k);
    const unc=clamp(18-Math.min(10,sorted.length*2)+(wc<40?5:0),6,22);
    return {rustmeter_score:rust,attention_score:attention,emotion_score:emotion,framing_score:framing,source_score:source,confidence_interval:`${clamp(rust-unc)}-${clamp(rust+unc)}`,top_signals:top.length?top:[{signal:'No strong influence signal found',reason:'The local scorer did not find enough high-confidence signals.',category:'baseline',location:'style'}],category_scores:norm,tactics,content_type:content.surface||'page',site_name:content.site_name||'This page',page_title:content.page_title||headline||'',host:content.host||'',word_count:wc,source:'local_rules',engine_version:ENGINE_VERSION,request_id:requestId,explanations:[`${rust>=66?'High':rust>=36?'Moderate':'Low'} Rustmeter influence pressure based on local scoring of ${content.surface||'page'} content.`,`Primary signals: ${tactics.length?tactics.slice(0,3).map(toTitle).join(', '):'few clear pressure tactics'}.`,`Analyzed ${wc} words locally.`]};
  }
  return {ENGINE_VERSION,SIGNALS,CATEGORY_KEYS,scoreContent,toTitle};
}));
