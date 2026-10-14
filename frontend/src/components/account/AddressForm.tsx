import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect } from 'react';
import { useForm } from 'react-hook-form';

import type { Address, AddressInput } from '@/api/queries/account';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Feedback';
import { FormField, Input, Select } from '@/components/ui/Field';
import { applyServerErrors, errorMessage } from '@/lib/forms';
import { addressSchema, INDIAN_STATES, type AddressFormValues } from '@/lib/validation/account';

const FIELDS = [
  'label',
  'full_name',
  'phone',
  'line1',
  'line2',
  'landmark',
  'city',
  'state',
  'pincode',
] as const;

export function toAddressInput(values: AddressFormValues): AddressInput {
  return {
    ...values,
    label: values.label || null,
    line2: values.line2 || null,
    landmark: values.landmark || null,
  };
}

function defaults(address?: Address): AddressFormValues {
  return {
    label: address?.label ?? '',
    full_name: address?.full_name ?? '',
    phone: address?.phone ?? '',
    line1: address?.line1 ?? '',
    line2: address?.line2 ?? '',
    landmark: address?.landmark ?? '',
    city: address?.city ?? '',
    state:
      (address?.state as AddressFormValues['state'] | undefined) ??
      ('' as AddressFormValues['state']),
    pincode: address?.pincode ?? '',
    is_default_shipping: address?.is_default_shipping ?? false,
    is_default_billing: address?.is_default_billing ?? false,
  };
}

/** Indian delivery address form with mobile-friendly inputs and autocomplete hints. */
export function AddressForm({
  address,
  onSubmit,
  submitting,
  error,
  submitLabel = 'Save address',
  showDefaults = true,
}: {
  address?: Address;
  onSubmit: (values: AddressInput) => void;
  submitting: boolean;
  error: unknown;
  submitLabel?: string;
  showDefaults?: boolean;
}) {
  const form = useForm<AddressFormValues>({
    resolver: zodResolver(addressSchema),
    defaultValues: defaults(address),
  });
  const { errors } = form.formState;

  const { setError } = form;
  useEffect(() => {
    if (error) applyServerErrors(error, setError, FIELDS);
  }, [error, setError]);

  return (
    <form
      noValidate
      className="space-y-5"
      onSubmit={form.handleSubmit(
        (values) => {
          onSubmit(toAddressInput(values));
        },
        (fieldErrors) => {
          const first = FIELDS.find((f) => f in fieldErrors);
          if (first) form.setFocus(first);
        },
      )}
    >
      {error ? <Alert tone="danger" title={errorMessage(error)} /> : null}
      <div className="grid gap-5 sm:grid-cols-2">
        <FormField label="Full name" required error={errors.full_name?.message}>
          <Input autoComplete="name" {...form.register('full_name')} />
        </FormField>
        <FormField label="Mobile number" required error={errors.phone?.message}>
          <Input type="tel" inputMode="tel" autoComplete="tel" {...form.register('phone')} />
        </FormField>
      </div>
      <FormField label="House / flat, building, street" required error={errors.line1?.message}>
        <Input autoComplete="address-line1" {...form.register('line1')} />
      </FormField>
      <FormField label="Area, locality" hint="Optional" error={errors.line2?.message}>
        <Input autoComplete="address-line2" {...form.register('line2')} />
      </FormField>
      <FormField label="Landmark" hint="Optional" error={errors.landmark?.message}>
        <Input {...form.register('landmark')} />
      </FormField>
      <div className="grid gap-5 sm:grid-cols-3">
        <FormField label="PIN code" required error={errors.pincode?.message}>
          <Input
            inputMode="numeric"
            autoComplete="postal-code"
            maxLength={6}
            {...form.register('pincode')}
          />
        </FormField>
        <FormField label="City" required error={errors.city?.message}>
          <Input autoComplete="address-level2" {...form.register('city')} />
        </FormField>
        <FormField label="State / UT" required error={errors.state?.message}>
          <Select autoComplete="address-level1" {...form.register('state')}>
            <option value="">Choose…</option>
            {INDIAN_STATES.map((state) => (
              <option key={state} value={state}>
                {state}
              </option>
            ))}
          </Select>
        </FormField>
      </div>
      <FormField label="Label" hint="Optional, e.g. Home or Office" error={errors.label?.message}>
        <Input {...form.register('label')} />
      </FormField>
      {showDefaults && (
        <fieldset className="space-y-2">
          <legend className="sr-only">Defaults</legend>
          <label className="flex items-center gap-3 text-sm">
            <input
              type="checkbox"
              className="size-4 accent-ink"
              {...form.register('is_default_shipping')}
            />
            Use as my default delivery address
          </label>
          <label className="flex items-center gap-3 text-sm">
            <input
              type="checkbox"
              className="size-4 accent-ink"
              {...form.register('is_default_billing')}
            />
            Use as my default billing address
          </label>
        </fieldset>
      )}
      <Button type="submit" loading={submitting}>
        {submitLabel}
      </Button>
    </form>
  );
}
