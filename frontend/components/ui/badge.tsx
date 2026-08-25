import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-primary text-primary-foreground',
        secondary: 'border-transparent bg-secondary text-secondary-foreground',
        outline: 'border-border text-foreground',
        normal: 'border-transparent bg-[color:var(--status-normal)]/10 text-[color:var(--status-normal)]',
        attention: 'border-transparent bg-[color:var(--status-attention)]/10 text-[color:var(--status-attention)]',
        emergency: 'border-transparent bg-[color:var(--status-emergency)]/10 text-[color:var(--status-emergency)]',
        offline: 'border-transparent bg-[color:var(--status-offline)]/10 text-[color:var(--status-offline)]',
      },
    },
    defaultVariants: { variant: 'default' },
  }
);

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
