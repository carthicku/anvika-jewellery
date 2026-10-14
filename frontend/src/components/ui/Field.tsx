import {
  cloneElement,
  forwardRef,
  isValidElement,
  useId,
  type InputHTMLAttributes,
  type ReactElement,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from 'react';

import { cn } from '@/lib/cn';

const control =
  'block w-full rounded-sm border border-line-strong bg-surface px-3.5 py-2.5 text-ink placeholder:text-ink-subtle transition-colors focus-visible:border-ink focus-visible:outline-2 focus-visible:outline-offset-0 aria-invalid:border-danger disabled:bg-surface-muted disabled:text-ink-subtle';

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...props }, ref) {
    return <input ref={ref} className={cn(control, 'min-h-11', className)} {...props} />;
  },
);

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement>
>(function Textarea({ className, ...props }, ref) {
  return <textarea ref={ref} className={cn(control, 'min-h-32', className)} {...props} />;
});

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className, children, ...props }, ref) {
    return (
      <select
        ref={ref}
        className={cn(
          control,
          'min-h-11 appearance-none bg-[url("data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2020%2020%22%20fill%3D%22none%22%20stroke%3D%22%231F1D1A%22%20stroke-width%3D%221.5%22%3E%3Cpath%20d%3D%22M6%208l4%204%204-4%22%2F%3E%3C%2Fsvg%3E")] bg-[length:1.25rem] bg-[right_0.75rem_center] bg-no-repeat pr-10',
          className,
        )}
        {...props}
      >
        {children}
      </select>
    );
  },
);

interface FormFieldProps {
  label: string;
  /** The input/select/textarea. It receives id, aria-describedby and aria-invalid automatically. */
  children: ReactElement<Record<string, unknown>>;
  hint?: ReactNode;
  error?: string;
  required?: boolean;
  className?: string;
  /** Visually hide the label (it stays available to screen readers). */
  hideLabel?: boolean;
}

/** Label + control + hint + error, wired together for assistive technology. */
export function FormField({
  label,
  children,
  hint,
  error,
  required,
  className,
  hideLabel,
}: FormFieldProps) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(' ') || undefined;
  const control = isValidElement(children)
    ? cloneElement(children, {
        id,
        'aria-describedby': describedBy,
        'aria-invalid': error ? true : undefined,
        'aria-required': required || undefined,
      })
    : children;

  return (
    <div className={cn('space-y-1.5', className)}>
      <label
        htmlFor={id}
        className={cn('block text-sm font-medium text-ink', hideLabel && 'sr-only')}
      >
        {label}
        {required && (
          <span aria-hidden="true" className="ml-0.5 text-ink-muted">
            *
          </span>
        )}
      </label>
      {control}
      {hint && (
        <p id={hintId} className="text-sm text-ink-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="text-sm text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
