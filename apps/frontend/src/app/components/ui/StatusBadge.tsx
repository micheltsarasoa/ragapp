import { cn } from './utils';

interface StatusBadgeProps {
  variant: 'success' | 'warning' | 'neutral' | 'danger';
  className?: string;
  children: React.ReactNode;
}

const VARIANT_CLASSES: Record<StatusBadgeProps['variant'], string> = {
  success: 'bg-success-dark  text-success',
  warning: 'bg-warning-dark  text-warning',
  neutral: 'bg-surface-2     text-secondary',
  danger:  'bg-red-950       text-red-400',
};

export function StatusBadge({ variant, className, children }: StatusBadgeProps) {
  return (
    <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs', VARIANT_CLASSES[variant], className)}>
      {children}
    </span>
  );
}
