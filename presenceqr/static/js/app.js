(function(){
  const btn=document.getElementById('themeBtn');
  function setTheme(t){document.documentElement.dataset.theme=t;try{localStorage.setItem('theme',t)}catch(e){};if(btn)btn.textContent=t==='dark'?'☀':'◐'}
  setTheme(document.documentElement.dataset.theme||'light');
  if(btn)btn.addEventListener('click',()=>setTheme(document.documentElement.dataset.theme==='dark'?'light':'dark'));
})();
