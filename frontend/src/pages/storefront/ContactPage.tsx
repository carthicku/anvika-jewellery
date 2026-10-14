import { zodResolver } from '@hookform/resolvers/zod';
import { Mail, MapPin, Phone } from 'lucide-react';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { ApiError } from '@/api/client';
import { useContactForm, usePublicSettings } from '@/api/queries/catalogue';
import { Container, PageHeader, PageMeta } from '@/components/layout/Page';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Feedback';
import { FormField, Input, Textarea } from '@/components/ui/Field';
import { secondsSince } from '@/lib/formTiming';

const schema = z.object({
  name: z.string().trim().min(2, 'Please enter your name.').max(120),
  email: z.email('Enter a valid email address.'),
  phone: z
    .string()
    .trim()
    .max(20)
    .refine((v) => v === '' || /^\+?[0-9 -]{7,20}$/.test(v), 'Enter a valid phone number.'),
  subject: z.string().trim().min(2, 'Please add a subject.').max(160),
  message: z
    .string()
    .trim()
    .min(10, 'Please write at least 10 characters.')
    .max(5000, 'Please keep your message under 5,000 characters.'),
  website: z.string().max(200),
});
type Values = z.infer<typeof schema>;

export function ContactPage() {
  const settings = usePublicSettings();
  const contact = useContactForm();
  const [openedAt] = useState(() => Date.now());
  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { name: '', email: '', phone: '', subject: '', message: '', website: '' },
  });

  const onSubmit = handleSubmit(
    (values) => {
      contact.mutate(
        {
          ...values,
          phone: values.phone || null,
          elapsed_seconds: secondsSince(openedAt),
        },
        {
          onSuccess: () => {
            reset();
          },
          onError: (error) => {
            if (error instanceof ApiError) {
              Object.entries(error.fieldErrors).forEach(([field, message]) => {
                if (field in values) setError(field as keyof Values, { message });
              });
            }
          },
        },
      );
    },
    (fieldErrors) => {
      const first = Object.keys(fieldErrors)[0];
      if (first) document.getElementsByName(first)[0]?.focus();
    },
  );

  const s = settings.data;

  return (
    <>
      <PageMeta
        title="Contact us"
        description="Questions about a piece, an order or sizing? Write to us."
        path="/contact"
      />
      <Container className="pb-20">
        <PageHeader
          eyebrow="We’re here to help"
          title="Contact us"
          description="Questions about a piece, sizing or an order? Send us a message and we’ll reply by email."
        />
        <div className="grid gap-12 lg:grid-cols-[1fr_20rem]">
          <div>
            {contact.isSuccess ? (
              <Alert tone="success" title="Thank you — your message has been sent.">
                We’ll reply to the email address you gave us.
              </Alert>
            ) : (
              <form onSubmit={onSubmit} noValidate className="space-y-5">
                <div className="grid gap-5 sm:grid-cols-2">
                  <FormField label="Name" required error={errors.name?.message}>
                    <Input autoComplete="name" {...register('name')} />
                  </FormField>
                  <FormField label="Email" required error={errors.email?.message}>
                    <Input type="email" autoComplete="email" {...register('email')} />
                  </FormField>
                </div>
                <FormField label="Phone" hint="Optional" error={errors.phone?.message}>
                  <Input type="tel" autoComplete="tel" inputMode="tel" {...register('phone')} />
                </FormField>
                <FormField label="Subject" required error={errors.subject?.message}>
                  <Input {...register('subject')} />
                </FormField>
                <FormField label="Message" required error={errors.message?.message}>
                  <Textarea rows={6} {...register('message')} />
                </FormField>
                <div aria-hidden="true" className="hidden">
                  <label htmlFor="contact-website">Website</label>
                  <input
                    id="contact-website"
                    tabIndex={-1}
                    autoComplete="off"
                    {...register('website')}
                  />
                </div>
                {contact.isError && (
                  <Alert tone="danger" title="We couldn’t send your message">
                    {contact.error instanceof ApiError && contact.error.code === 'RATE_LIMITED'
                      ? 'You have sent several messages recently. Please try again later.'
                      : 'Please check your connection and try again.'}
                  </Alert>
                )}
                <Button type="submit" size="lg" loading={contact.isPending}>
                  Send message
                </Button>
              </form>
            )}
          </div>

          <aside
            aria-label="Store contact details"
            className="space-y-6 rounded-md border border-line bg-surface p-6 text-sm"
          >
            <div className="flex gap-3">
              <Mail className="mt-0.5 size-4 text-gold" aria-hidden="true" />
              <p>{s?.support_email}</p>
            </div>
            <div className="flex gap-3">
              <Phone className="mt-0.5 size-4 text-gold" aria-hidden="true" />
              <p>
                {s?.support_phone}
                <br />
                <span className="text-ink-muted">{s?.business_hours}</span>
              </p>
            </div>
            <div className="flex gap-3">
              <MapPin className="mt-0.5 size-4 text-gold" aria-hidden="true" />
              <p>{s?.business_address}</p>
            </div>
          </aside>
        </div>
      </Container>
    </>
  );
}
