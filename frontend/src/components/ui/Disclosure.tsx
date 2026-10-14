import { Check, ChevronDown } from 'lucide-react';
import { Accordion as A, Checkbox as C } from 'radix-ui';
import type { ReactNode } from 'react';

import { cn } from '@/lib/cn';

export function Accordion({
  children,
  defaultValue,
  className,
}: {
  children: ReactNode;
  defaultValue?: string[];
  className?: string;
}) {
  return (
    <A.Root
      type="multiple"
      defaultValue={defaultValue}
      className={cn('divide-y divide-line border-y border-line', className)}
    >
      {children}
    </A.Root>
  );
}

export function AccordionItem({
  value,
  title,
  children,
}: {
  value: string;
  title: ReactNode;
  children: ReactNode;
}) {
  return (
    <A.Item value={value}>
      <A.Header>
        <A.Trigger className="group flex min-h-13 w-full items-center justify-between py-3 text-left text-sm font-medium tracking-wide">
          {title}
          <ChevronDown
            className="size-4 text-ink-muted transition-transform duration-200 group-data-[state=open]:rotate-180"
            aria-hidden="true"
          />
        </A.Trigger>
      </A.Header>
      <A.Content className="pb-5 text-sm leading-relaxed text-ink-muted">{children}</A.Content>
    </A.Item>
  );
}

/** Accessible checkbox with a visible label (Radix handles keyboard and ARIA). */
export function Checkbox({
  checked,
  onCheckedChange,
  label,
  count,
  id,
}: {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  label: ReactNode;
  count?: number;
  id: string;
}) {
  return (
    <div className="flex min-h-9 items-center gap-3">
      <C.Root
        id={id}
        checked={checked}
        onCheckedChange={(value) => {
          onCheckedChange(value === true);
        }}
        className="flex size-5 shrink-0 items-center justify-center rounded-sm border border-line-strong bg-surface data-[state=checked]:border-ink data-[state=checked]:bg-ink"
      >
        <C.Indicator>
          <Check className="size-3.5 text-ivory" strokeWidth={2.5} aria-hidden="true" />
        </C.Indicator>
      </C.Root>
      <label
        htmlFor={id}
        className="flex flex-1 cursor-pointer items-center justify-between text-sm"
      >
        <span>{label}</span>
        {count !== undefined && <span className="tabular text-ink-subtle">{count}</span>}
      </label>
    </div>
  );
}
