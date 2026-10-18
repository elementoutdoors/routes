window.__writes=[];
(function(){
var DOCS=__DOCS__;
function snap(id,d){return {id:id,exists:d!==undefined,data:function(){return d===undefined?undefined:JSON.parse(JSON.stringify(d));},metadata:{}}}
var db={doc:function(p){return {get:function(){return Promise.resolve(snap(p.split('/').pop(),DOCS[p]))},onSnapshot:function(cb){setTimeout(function(){cb(snap(p.split('/').pop(),DOCS[p]))},50);return function(){}},set:function(d){window.__writes.push(['set',p,d]);DOCS[p]=d;return Promise.resolve()},update:function(d){window.__writes.push(['update',p,d]);return Promise.resolve()}}},
collection:function(c){var q={limit:function(){return q},onSnapshot:function(cb){setTimeout(function(){var ds=Object.keys(DOCS).filter(function(k){return k.indexOf(c+'/')===0}).map(function(k){return snap(k.split('/').pop(),DOCS[k])});cb({docs:ds,size:ds.length,empty:!ds.length})},60);return function(){}}};return q}};
var caps={db:db,user:{canEdit:function(){return true}},mcp:{callTool:function(){window.__writes.push(['fire']);return Promise.resolve({})}},assets:{upload:function(){return Promise.resolve({id:'a'.repeat(32)})}}};
window.claude={use:function(n){return Promise.resolve(caps[n]||null)}};
})();
