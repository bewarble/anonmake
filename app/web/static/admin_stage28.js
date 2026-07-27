(() => {
  const root = document.documentElement;
  const storedTheme = localStorage.getItem("anonmake-theme");
  if (storedTheme) root.dataset.theme = storedTheme;

  const sidebar = document.querySelector("[data-sidebar]");
  let backdrop = document.querySelector("[data-sidebar-backdrop]");
  if (!backdrop) {
    backdrop = document.createElement("div");
    backdrop.className = "sidebar-backdrop";
    backdrop.dataset.sidebarBackdrop = "";
    document.body.appendChild(backdrop);
  }

  const setSidebar = (open) => {
    sidebar?.classList.toggle("open", open);
    backdrop?.classList.toggle("open", open);
    document.body.style.overflow = open ? "hidden" : "";
  };

  document.querySelectorAll("[data-sidebar-toggle]").forEach((button) => {
    button.addEventListener("click", () => setSidebar(!sidebar?.classList.contains("open")));
  });
  document.querySelectorAll("[data-sidebar-close]").forEach((button) => {
    button.addEventListener("click", () => setSidebar(false));
  });
  backdrop?.addEventListener("click", () => setSidebar(false));
  document.querySelectorAll(".pro-nav a").forEach((link) => {
    link.addEventListener("click", () => {
      if (window.innerWidth <= 760) setSidebar(false);
    });
  });

  document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const next = root.dataset.theme === "light" ? "dark" : "light";
      root.dataset.theme = next;
      localStorage.setItem("anonmake-theme", next);
      renderAllCharts();
    });
  });

  const overlay = document.querySelector("[data-command-overlay]");
  const commandInput = document.querySelector("[data-command-input]");
  const openCommand = () => {
    if (!overlay) return;
    overlay.hidden = false;
    setTimeout(() => commandInput?.focus(), 0);
  };
  const closeCommand = () => { if (overlay) overlay.hidden = true; };

  document.querySelectorAll("[data-command-open]").forEach((button) => button.addEventListener("click", openCommand));
  overlay?.addEventListener("click", (event) => { if (event.target === overlay) closeCommand(); });
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault(); openCommand();
    }
    if (event.key === "Escape") { closeCommand(); setSidebar(false); }
  });

  const chartState = new WeakMap();

  function colors() {
    const s = getComputedStyle(root);
    return {
      text: s.getPropertyValue("--muted").trim() || "#8f9dbc",
      line: s.getPropertyValue("--line").trim() || "#263552",
      surface: s.getPropertyValue("--surface-2").trim() || "#172238",
      purple: s.getPropertyValue("--purple").trim() || "#8b7cff",
      cyan: s.getPropertyValue("--cyan").trim() || "#55d8ff",
      green: s.getPropertyValue("--green").trim() || "#52d3a7",
    };
  }

  function prepare(canvas) {
    const ratio = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = Math.max(1, Math.floor(rect.width * ratio));
    canvas.height = Math.max(1, Math.floor(rect.height * ratio));
    const ctx = canvas.getContext("2d");
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    return {ctx, width: rect.width, height: rect.height};
  }

  function parseData(canvas) {
    try { return JSON.parse(canvas.dataset.chart || "[]"); } catch { return []; }
  }

  function draw(canvas, data) {
    if (!data.length) return;
    const {ctx, width, height} = prepare(canvas);
    const c = colors();
    const pad = {left:36,right:16,top:18,bottom:32};
    const innerW = width-pad.left-pad.right;
    const innerH = height-pad.top-pad.bottom;
    const series = [
      {key:"users",color:c.purple,label:"Пользователи"},
      {key:"questions",color:c.cyan,label:"Сообщения"},
      {key:"answers",color:c.green,label:"Ответы"},
    ];
    const max = Math.max(1,...data.flatMap(row => series.map(s => Number(row[s.key]||0))));
    const previous = chartState.get(canvas);
    const state = {data, selected: previous?.selected ?? -1, x:[]};
    chartState.set(canvas,state);

    ctx.clearRect(0,0,width,height);
    ctx.strokeStyle=c.line; ctx.fillStyle=c.text; ctx.font="11px system-ui";
    for(let i=0;i<=4;i++){
      const y=pad.top+(innerH/4)*i;
      ctx.beginPath(); ctx.moveTo(pad.left,y); ctx.lineTo(width-pad.right,y); ctx.stroke();
      ctx.fillText(String(Math.round(max*(1-i/4))),3,y+4);
    }
    const xFor=i=>pad.left+(data.length===1?0:(innerW*i)/(data.length-1));
    const yFor=v=>pad.top+innerH-(Number(v||0)/max)*innerH;
    state.x=data.map((_,i)=>xFor(i));

    if(state.selected>=0){
      const x=xFor(state.selected);
      ctx.fillStyle=c.surface; ctx.fillRect(x-18,pad.top,36,innerH);
    }

    series.forEach(s=>{
      ctx.beginPath(); ctx.strokeStyle=s.color; ctx.lineWidth=2.5;
      data.forEach((row,i)=> i===0?ctx.moveTo(xFor(i),yFor(row[s.key])):ctx.lineTo(xFor(i),yFor(row[s.key])));
      ctx.stroke();
      data.forEach((row,i)=>{
        ctx.beginPath(); ctx.fillStyle=s.color;
        ctx.arc(xFor(i),yFor(row[s.key]),state.selected===i?5:3,0,Math.PI*2); ctx.fill();
      });
    });

    const every=Math.max(1,Math.ceil(data.length/7));
    data.forEach((row,i)=>{
      if(i%every!==0 && i!==data.length-1)return;
      ctx.fillStyle=c.text; ctx.fillText(row.label,xFor(i)-13,height-8);
    });

    canvas.style.cursor="pointer";
    canvas.onclick=(event)=>{
      const rect=canvas.getBoundingClientRect();
      const clickX=event.clientX-rect.left;
      let best=0,distance=Infinity;
      state.x.forEach((candidate,i)=>{
        const current=Math.abs(candidate-clickX);
        if(current<distance){distance=current;best=i;}
      });
      state.selected=best;
      draw(canvas,data);
      const row=data[best];
      const detail=canvas.parentElement?.querySelector("[data-chart-detail]");
      if(detail){
        detail.innerHTML="<strong>"+row.label+"</strong><br>"+
          "Пользователи: "+(row.users||0)+" · Сообщения: "+(row.questions||0)+
          " · Ответы: "+(row.answers||0)+" · Доход: "+
          Number(row.revenue||0).toLocaleString("ru-RU")+" ₽";
      }
    };
  }

  function renderAllCharts(){
    document.querySelectorAll("canvas[data-chart]:not(#businessChart)").forEach(canvas=>draw(canvas,parseData(canvas)));
  }

  let timer;
  window.addEventListener("resize",()=>{clearTimeout(timer);timer=setTimeout(renderAllCharts,120);});
  renderAllCharts();
})();
