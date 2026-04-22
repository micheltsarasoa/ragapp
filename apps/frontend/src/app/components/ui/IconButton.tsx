interface IconButtonProps {
  onClick?: () => void;
  title?: string;
  className?: string;
  children: React.ReactNode;
}

export function IconButton({ onClick, title, className = '', children }: IconButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      className={`p-2 rounded-lg text-muted-fg hover:bg-surface-2 transition-colors ${className}`}
    >
      {children}
    </button>
  );
}
