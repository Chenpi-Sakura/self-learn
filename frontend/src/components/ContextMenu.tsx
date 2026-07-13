import { useEffect, useRef } from 'react';
import './ContextMenu.css';

export interface ContextMenuItem {
  type: 'action' | 'separator';
  label?: string;
  icon?: string;
  shortcut?: string;
  disabled?: boolean;
  danger?: boolean;
  action?: () => void;
}

interface Props {
  x: number;
  y: number;
  items: ContextMenuItem[];
  onClose: () => void;
}

export function ContextMenu({ x, y, items, onClose }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    // 视口边界检测：如果菜单超出右/下边界，翻转方向
    const rect = el.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    let cx = x;
    let cy = y;
    if (x + rect.width > vw - 8) cx = vw - rect.width - 8;
    if (y + rect.height > vh - 8) cy = vh - rect.height - 8;
    el.style.left = `${Math.max(4, cx)}px`;
    el.style.top = `${Math.max(4, cy)}px`;
  }, [x, y]);

  // 全局点击关闭 & Escape 关闭
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    // 用 timeout 避免点击触发菜单的鼠标事件同时触发关闭
    const handleClick = () => setTimeout(onClose, 0);
    document.addEventListener('keydown', handleKey);
    document.addEventListener('click', handleClick);
    return () => {
      document.removeEventListener('keydown', handleKey);
      document.removeEventListener('click', handleClick);
    };
  }, [onClose]);

  return (
    <div className="ctx-menu" ref={ref} style={{ left: x, top: y }} role="menu">
      {items.map((item, i) => {
        if (item.type === 'separator') {
          return <div key={i} className="ctx-sep" role="separator" />;
        }
        return (
          <button
            key={i}
            className={`ctx-item${item.disabled ? ' disabled' : ''}${item.danger ? ' danger' : ''}`}
            role="menuitem"
            disabled={item.disabled}
            onClick={(e) => {
              e.stopPropagation();
              if (!item.disabled) {
                item.action?.();
                onClose();
              }
            }}
          >
            {item.icon && <span className="ctx-ic">{item.icon}</span>}
            <span className="ctx-lb">{item.label}</span>
            {item.shortcut && <span className="ctx-sc">{item.shortcut}</span>}
          </button>
        );
      })}
    </div>
  );
}
