import { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ArrowUpRight, Menu, X } from 'lucide-react';

// Navigation card definitions
const CARDS = [
  {
    label: 'Анализ права',
    bg: 'rgba(99,102,241,0.12)',
    border: 'rgba(99,102,241,0.25)',
    links: [
      { label: 'Поиск НПА', href: '/' },
      { label: 'Глубокий анализ', href: '/analyze' },
      { label: 'Сравнить версии', href: '/diff' },
    ],
  },
  {
    label: 'База данных',
    bg: 'rgba(16,185,129,0.08)',
    border: 'rgba(16,185,129,0.20)',
    links: [
      { label: 'Индексация НПА', href: '/index' },
      { label: 'Аудит O(N)', href: '/audit' },
      { label: 'Граф & Heatmap', href: '/graph' },
    ],
  },
  {
    label: 'Настройки',
    bg: 'rgba(245,158,11,0.08)',
    border: 'rgba(245,158,11,0.20)',
    links: [
      { label: 'AI-провайдер', href: '/settings' },
      { label: 'Qwen / Azure / OpenAI', href: '/settings' },
    ],
  },
];

export default function NavSidebar() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const navRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (navRef.current && !navRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Close on route change
  useEffect(() => { setOpen(false); }, [location.pathname]);

  const go = (href: string) => {
    navigate(href);
    setOpen(false);
  };

  return (
    <div
      ref={navRef}
      className="absolute left-1/2 -translate-x-1/2 top-4 z-50 w-[92%] max-w-[820px]"
    >
      {/* Nav bar */}
      <nav
        className="relative rounded-2xl overflow-hidden transition-all duration-300"
        style={{
          background: 'rgba(15,18,35,0.72)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          border: '1px solid rgba(255,255,255,0.08)',
          boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
        }}
      >
        {/* Top bar */}
        <div className="flex items-center justify-between px-5 h-14">
          {/* Logo */}
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center font-bold text-white text-sm shadow-lg shadow-indigo-500/30">
              L
            </div>
            <span className="font-bold text-white text-sm tracking-wide">LexEntropy</span>
          </div>

          {/* Center links (desktop) */}
          <div className="hidden md:flex items-center gap-1">
            {['/', '/analyze', '/diff', '/graph', '/settings'].map((path, i) => {
              const labels = ['Поиск', 'Анализ', 'Сравнение', 'Граф', 'Настройки'];
              const active = location.pathname === path || (path !== '/' && location.pathname.startsWith(path));
              return (
                <button
                  key={path}
                  onClick={() => go(path)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    active
                      ? 'bg-white/10 text-white'
                      : 'text-white/50 hover:text-white hover:bg-white/5'
                  }`}
                >
                  {labels[i]}
                </button>
              );
            })}
          </div>

          {/* Right: CTA + hamburger */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => go('/settings')}
              className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold transition-all shadow-lg shadow-indigo-600/30"
            >
              AI Настройки
            </button>

            <button
              onClick={() => setOpen(v => !v)}
              className="md:hidden w-8 h-8 rounded-lg flex items-center justify-center text-white/70 hover:text-white hover:bg-white/10 transition"
              aria-label="Toggle menu"
            >
              {open ? <X size={18} /> : <Menu size={18} />}
            </button>

            {/* Desktop hamburger for cards */}
            <button
              onClick={() => setOpen(v => !v)}
              className="hidden md:flex w-8 h-8 rounded-lg flex items-center justify-center text-white/70 hover:text-white hover:bg-white/10 transition"
              aria-label="Expand cards"
            >
              {open ? <X size={18} /> : <Menu size={18} />}
            </button>
          </div>
        </div>

        {/* Expandable cards panel */}
        <div
          className="overflow-hidden transition-all duration-300 ease-out"
          style={{ maxHeight: open ? '320px' : '0px', opacity: open ? 1 : 0 }}
        >
          <div className="p-2 pt-0 flex flex-col md:flex-row gap-2 pb-2">
            {CARDS.map((card, idx) => (
              <div
                key={idx}
                className="flex-1 rounded-xl p-4 flex flex-col gap-3 transition-all duration-200"
                style={{
                  background: card.bg,
                  border: `1px solid ${card.border}`,
                  transform: open ? 'translateY(0)' : 'translateY(12px)',
                  transitionDelay: `${idx * 60}ms`,
                }}
              >
                <div className="text-base font-semibold text-white tracking-tight">
                  {card.label}
                </div>
                <div className="flex flex-col gap-1">
                  {card.links.map((lnk, i) => (
                    <button
                      key={i}
                      onClick={() => go(lnk.href)}
                      className={`flex items-center gap-1.5 text-sm text-left transition-opacity hover:opacity-100 py-0.5 ${
                        location.pathname === lnk.href ? 'text-white font-medium' : 'text-white/55'
                      }`}
                    >
                      <ArrowUpRight size={13} className="shrink-0 opacity-70" />
                      {lnk.label}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </nav>
    </div>
  );
}
