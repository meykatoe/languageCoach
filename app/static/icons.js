// Minimal line-icon set (stroke-based, no emoji) shared across pages.
const Icons = {
  gear: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z"/><path d="M19.4 13a7.4 7.4 0 0 0 .06-1l1.86-1.46a.9.9 0 0 0 .2-1.15l-1.76-3.05a.9.9 0 0 0-1.09-.39l-2.2.88a7.3 7.3 0 0 0-1.73-1l-.33-2.34a.9.9 0 0 0-.89-.77h-3.52a.9.9 0 0 0-.89.77l-.33 2.34c-.63.25-1.21.58-1.73 1l-2.2-.88a.9.9 0 0 0-1.09.39L1.94 9.4a.9.9 0 0 0 .2 1.15L4 12a7.4 7.4 0 0 0 0 2l-1.86 1.46a.9.9 0 0 0-.2 1.15l1.76 3.05c.24.4.72.57 1.15.39l2.2-.88c.52.42 1.1.75 1.73 1l.33 2.34c.07.44.46.77.89.77h3.52c.43 0 .82-.33.89-.77l.33-2.34c.63-.25 1.21-.58 1.73-1l2.2.88c.43.18.91.01 1.15-.39l1.76-3.05a.9.9 0 0 0-.2-1.15L19.4 13Z"/></svg>',
  speaker: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 9v6h3.5L13 19V5L7.5 9H4Z"/><path d="M16.5 8.5a5 5 0 0 1 0 7"/><path d="M19 6a9 9 0 0 1 0 12"/></svg>',
  mic: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0"/><path d="M12 18v3"/><path d="M9 21h6"/></svg>',
  stop: '<svg class="icon" viewBox="0 0 24 24" fill="currentColor" stroke="none"><rect x="7" y="7" width="10" height="10" rx="2"/></svg>',
  sparkle: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v4M12 17v4M3 12h4M17 12h4"/><path d="M12 8a4 4 0 0 0 4 4 4 4 0 0 0-4 4 4 4 0 0 0-4-4 4 4 0 0 0 4-4Z"/></svg>',
  bolt: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2 4 14h6l-1 8 9-12h-6l1-8Z"/></svg>',
};

function iconHtml(name, extraClass) {
  return (Icons[name] || '').replace('class="icon"', `class="icon${extraClass ? ' ' + extraClass : ''}"`);
}
