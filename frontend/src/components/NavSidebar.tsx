import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useStore } from '../store/useStore';
import { FlaskConical, GitCompareArrows, Menu, Network, Search, Settings, ShieldAlert, X } from 'lucide-react';

const NAV_ITEMS = [
  { path: '/', label: 'Поиск', icon: Search },
  { path: '/analyze', label: 'Анализ', icon: FlaskConical },
  { path: '/diff', label: 'Сравнение', icon: GitCompareArrows },
  { path: '/audit', label: 'Аудит', icon: ShieldAlert },
  { path: '/graph', label: 'Граф', icon: Network },
  { path: '/settings', label: 'Настройки', icon: Settings },
];

export default function NavSidebar() {
  const [open, setOpen] = useState(false);
  const { activeScope, selectedDocId } = useStore();
  const navigate = useNavigate();
  const location = useLocation();
  const navRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (event: MouseEvent) => {
      if (navRef.current && !navRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };

    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const go = (path: string) => {
    const target = path === '/analyze' && selectedDocId ? `/analyze/${selectedDocId}` : path;
    navigate(target);
    setOpen(false);
  };

  return (
    <div ref={navRef} className="absolute left-1/2 -translate-x-1/2 top-4 z-50 w-[94%] max-w-[860px]">
      <nav
        className="relative rounded-2xl overflow-hidden transition-all duration-300"
        style={{
          background: 'rgba(255, 255, 255, 0.7)',
          backdropFilter: 'blur(28px) saturate(110%)',
          WebkitBackdropFilter: 'blur(28px) saturate(110%)',
          border: '1px solid rgba(183, 120, 62, 0.15)',
          boxShadow: '0 8px 40px rgba(183, 120, 62, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.5)',
        }}
      >
        <div className="flex items-center justify-between px-5 h-14">
          <div className="w-8 md:w-24 pointer-events-none" />

          <div className="hidden md:flex items-center gap-0.5">
            {NAV_ITEMS.map((item) => {
              const active = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path));
              const Icon = item.icon;

              return (
                <button
                  key={item.path}
                  onClick={() => go(item.path)}
                  className={`px-3.5 py-1.5 rounded-lg text-[13px] font-medium transition-all flex items-center gap-2 ${
                    active ? 'bg-primary/10 text-primary border border-primary/20' : 'text-textMuted hover:text-textSub hover:bg-black/[0.03]'
                  }`}
                >
                  <Icon size={14} className={active ? 'text-primary' : 'opacity-60'} />
                  {item.label}
                  {item.path === '/analyze' && activeScope.length > 0 && (
                    <span className="w-4 h-4 bg-primary/20 text-primary text-[10px] flex items-center justify-center rounded-full font-bold">
                      {activeScope.length}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          <button
            onClick={() => setOpen((value) => !value)}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-textMuted hover:text-primary hover:bg-primary/5 transition"
            aria-label="Toggle menu"
          >
            {open ? <X size={16} /> : <Menu size={16} />}
          </button>
        </div>

        <div className="overflow-hidden transition-all duration-300 ease-out" style={{ maxHeight: open ? '300px' : '0px', opacity: open ? 1 : 0 }}>
          <div className="px-4 pb-4">
            <div className="divider-amber mb-4" />
            <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
              {NAV_ITEMS.map((item) => {
                const active = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path));
                const Icon = item.icon;

                return (
                  <button
                    key={item.path}
                    onClick={() => go(item.path)}
                    className={`flex flex-col items-center gap-2 py-4 rounded-xl transition-all ${
                      active
                        ? 'bg-primary/10 border border-primary/20 text-primary'
                        : 'bg-black/[0.02] border border-transparent text-textMuted hover:text-textSub hover:bg-black/[0.04] hover:border-borderLight'
                    }`}
                  >
                    <Icon size={20} />
                    <span className="text-xs font-medium">{item.label}</span>
                  </button>
                );
              })}
            </div>

            {activeScope.length > 0 && (
              <div className="mt-3 flex items-center gap-2 bg-primary/5 border border-primary/10 rounded-lg px-3 py-2">
                <span className="text-[10px] text-primary font-mono uppercase tracking-wider">Scope</span>
                <div className="flex gap-1 flex-wrap">
                  {activeScope.map((id) => (
                    <span key={id} className="text-[10px] font-mono bg-primary/10 text-primary/80 px-2 py-0.5 rounded">
                      {id}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </nav>
    </div>
  );
}