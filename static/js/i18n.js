/* ── Auto-translate UI labels based on device language ──────────── */
/* Any element with data-i18n="key" gets the label for the visitor's
   browser language. Content stays in English; only short labels change. */
(function(){
  var T = {
    en:{about:"About",resume:"Resume",portfolio:"Portfolio",accomplishments:"Accomplishments",download:"Download Resume",github:"GitHub",websites:"Websites",noLinks:"No links yet.",noAccomp:"No accomplishments yet.",noPhoto:"No photo uploaded",home:"Home",experience:"Experience",skills:"Education & Skills",projects:"Projects",contact:"Contact",menu:"Menu"},
    pt:{about:"Sobre",resume:"Currículo",portfolio:"Portfólio",accomplishments:"Conquistas",download:"Baixar Currículo",github:"GitHub",websites:"Sites",noLinks:"Nenhum link ainda.",noAccomp:"Nenhuma conquista ainda.",noPhoto:"Nenhuma foto enviada",home:"Início",experience:"Experiência",skills:"Formação e Habilidades",projects:"Projetos",contact:"Contato",menu:"Menu"},
    es:{about:"Acerca de",resume:"Currículum",portfolio:"Portafolio",accomplishments:"Logros",download:"Descargar Currículum",github:"GitHub",websites:"Sitios web",noLinks:"Sin enlaces aún.",noAccomp:"Sin logros aún.",noPhoto:"Sin foto subida",home:"Inicio",experience:"Experiencia",skills:"Educación y Habilidades",projects:"Proyectos",contact:"Contacto",menu:"Menú"},
    fr:{about:"À propos",resume:"CV",portfolio:"Portfolio",accomplishments:"Réalisations",download:"Télécharger le CV",github:"GitHub",websites:"Sites web",noLinks:"Aucun lien encore.",noAccomp:"Aucune réalisation encore.",noPhoto:"Aucune photo",home:"Accueil",experience:"Expérience",skills:"Formation et compétences",projects:"Projets",contact:"Contact",menu:"Menu"},
    de:{about:"Über mich",resume:"Lebenslauf",portfolio:"Portfolio",accomplishments:"Erfolge",download:"Lebenslauf herunterladen",github:"GitHub",websites:"Webseiten",noLinks:"Noch keine Links.",noAccomp:"Noch keine Erfolge.",noPhoto:"Kein Foto hochgeladen",home:"Startseite",experience:"Erfahrung",skills:"Ausbildung & Fähigkeiten",projects:"Projekte",contact:"Kontakt",menu:"Menü"},
    it:{about:"Chi sono",resume:"Curriculum",portfolio:"Portfolio",accomplishments:"Risultati",download:"Scarica il Curriculum",github:"GitHub",websites:"Siti web",noLinks:"Nessun link ancora.",noAccomp:"Nessun risultato ancora.",noPhoto:"Nessuna foto caricata",home:"Home",experience:"Esperienza",skills:"Formazione e competenze",projects:"Progetti",contact:"Contatti",menu:"Menu"},
    ja:{about:"経歴",resume:"履歴書",portfolio:"ポートフォリオ",accomplishments:"実績",download:"履歴書をダウンロード",github:"GitHub",websites:"ウェブサイト",noLinks:"リンクなし",noAccomp:"実績なし",noPhoto:"写真なし",home:"ホーム",experience:"職歴",skills:"学歴とスキル",projects:"プロジェクト",contact:"お問い合わせ",menu:"メニュー"},
    ko:{about:"소개",resume:"이력서",portfolio:"포트폴리오",accomplishments:"성과",download:"이력서 다운로드",github:"GitHub",websites:"웹사이트",noLinks:"링크 없음",noAccomp:"성과 없음",noPhoto:"사진 없음",home:"홈",experience:"경력",skills:"학력 및 기술",projects:"프로젝트",contact:"연락처",menu:"메뉴"},
    zh:{about:"关于",resume:"简历",portfolio:"作品集",accomplishments:"成就",download:"下载简历",github:"GitHub",websites:"网站",noLinks:"暂无链接",noAccomp:"暂无成就",noPhoto:"无照片",home:"首页",experience:"工作经历",skills:"教育与技能",projects:"项目",contact:"联系",menu:"菜单"}
  };
  var lang = (navigator.language || navigator.userLanguage || "en").split("-")[0].toLowerCase();
  var t = T[lang] || T.en;
  window.__T = t;
  document.querySelectorAll("[data-i18n]").forEach(function(el){
    var key = el.getAttribute("data-i18n");
    if(t[key]) el.textContent = t[key];
  });
})();
