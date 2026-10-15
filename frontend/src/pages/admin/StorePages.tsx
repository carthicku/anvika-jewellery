import { Plus, Trash2 } from 'lucide-react';
import { lazy, Suspense, useState } from 'react';

import { useMe } from '@/api/queries/account';
import {
  useAdminCategories,
  useAdminCollections,
  useAdminSettings,
  useContentPages,
  useCoupons,
  useDeleteShippingZone,
  useDiscounts,
  useSaveContentPage,
  useSaveCoupon,
  useSaveDiscount,
  useSaveSettings,
  useSaveShippingMethod,
  useSaveShippingZone,
  useShippingMethods,
  useShippingZones,
  useStaffAction,
  useStaffUsers,
  type ContentPageAdmin,
  type Coupon,
  type Discount,
  type ShippingMethod,
  type ShippingZone,
} from '@/api/queries/admin';
import { AdminPage, DataTable, FormDialog, Panel, field } from '@/components/admin/AdminUI';
import { Button } from '@/components/ui/Button';
import { Alert, Badge, ErrorState, Skeleton } from '@/components/ui/Feedback';
import { FormField, Input, Select, Textarea } from '@/components/ui/Field';
import { useToast } from '@/components/ui/Toaster';
import { formatDateTime, formatMoney } from '@/lib/format';
import { errorMessage } from '@/lib/forms';

const Markdown = lazy(() => import('react-markdown'));

function opt(value: string): string | null {
  return value === '' ? null : value;
}

/** <input type="datetime-local"> value (local time) → ISO string with the browser's offset. */
function toIso(local: string): string {
  return new Date(local).toISOString();
}

function toLocalInput(iso: string | null | undefined): string {
  if (!iso) return '';
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${String(d.getFullYear())}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

const nowLocal = () => toLocalInput(new Date().toISOString());

// --------------------------------------------------------------------------- promotions

const DISCOUNT_KINDS = {
  percent_off_making: '% off making charges',
  percent_off_price: '% off the price',
  flat_off_price: '₹ off the price',
} as const;

function DiscountDialog({ discount }: { discount?: Discount }) {
  const save = useSaveDiscount();
  const categories = useAdminCategories();
  const collections = useAdminCollections();
  const [scope, setScope] = useState(discount?.scope ?? 'all');
  return (
    <FormDialog
      title={discount ? `Edit ${discount.name}` : 'New automatic discount'}
      description="Applied automatically to matching pieces; when several apply, the customer gets the best one."
      submitLabel="Save discount"
      trigger={(open) =>
        discount ? (
          <Button size="sm" variant="ghost" onClick={open}>
            Edit
          </Button>
        ) : (
          <Button size="sm" variant="secondary" onClick={open}>
            <Plus className="size-4" aria-hidden="true" /> New discount
          </Button>
        )
      }
      onSubmit={(form) =>
        save.mutateAsync({
          id: discount?.id,
          body: {
            name: field(form, 'name'),
            kind: field(form, 'kind') as keyof typeof DISCOUNT_KINDS,
            value: field(form, 'value'),
            scope: scope as 'all' | 'category' | 'collection' | 'product',
            scope_id: scope === 'all' ? null : opt(field(form, 'scope_id')),
            starts_at: toIso(field(form, 'starts_at')),
            ends_at: field(form, 'ends_at') ? toIso(field(form, 'ends_at')) : null,
            is_active: form.get('is_active') === 'on',
          },
        })
      }
    >
      <FormField label="Name" required>
        <Input name="name" required defaultValue={discount?.name} />
      </FormField>
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="Type">
          <Select name="kind" defaultValue={discount?.kind ?? 'percent_off_making'}>
            {Object.entries(DISCOUNT_KINDS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </Select>
        </FormField>
        <FormField label="Value" required>
          <Input name="value" required inputMode="decimal" defaultValue={discount?.value} />
        </FormField>
        <FormField label="Applies to">
          <Select
            value={scope}
            onChange={(e) => {
              setScope(e.target.value);
            }}
          >
            <option value="all">Everything</option>
            <option value="category">A category</option>
            <option value="collection">A collection</option>
          </Select>
        </FormField>
        {scope !== 'all' && (
          <FormField label={scope === 'category' ? 'Category' : 'Collection'} required>
            <Select name="scope_id" required defaultValue={discount?.scope_id ?? ''}>
              <option value="">Choose…</option>
              {(scope === 'category' ? categories.data : collections.data)?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </FormField>
        )}
        <FormField label="Starts" required>
          <Input
            name="starts_at"
            type="datetime-local"
            required
            defaultValue={toLocalInput(discount?.starts_at) || nowLocal()}
          />
        </FormField>
        <FormField label="Ends" hint="Optional">
          <Input
            name="ends_at"
            type="datetime-local"
            defaultValue={toLocalInput(discount?.ends_at)}
          />
        </FormField>
      </div>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          name="is_active"
          defaultChecked={discount?.is_active ?? true}
          className="size-4 accent-ink"
        />{' '}
        Active
      </label>
    </FormDialog>
  );
}

function CouponDialog({ coupon }: { coupon?: Coupon }) {
  const save = useSaveCoupon();
  return (
    <FormDialog
      title={coupon ? `Edit ${coupon.code}` : 'New coupon'}
      description="Customers enter the code in their cart. Limits are enforced at checkout."
      submitLabel="Save coupon"
      trigger={(open) =>
        coupon ? (
          <Button size="sm" variant="ghost" onClick={open}>
            Edit
          </Button>
        ) : (
          <Button size="sm" variant="secondary" onClick={open}>
            <Plus className="size-4" aria-hidden="true" /> New coupon
          </Button>
        )
      }
      onSubmit={(form) => {
        const body = {
          description: opt(field(form, 'description')),
          kind: field(form, 'kind') as 'percent' | 'flat',
          value: field(form, 'value'),
          max_discount_amount: opt(field(form, 'max_discount_amount')),
          min_order_amount: opt(field(form, 'min_order_amount')),
          starts_at: toIso(field(form, 'starts_at')),
          ends_at: field(form, 'ends_at') ? toIso(field(form, 'ends_at')) : null,
          usage_limit_total: field(form, 'usage_limit_total')
            ? Number(field(form, 'usage_limit_total'))
            : null,
          usage_limit_per_customer: field(form, 'usage_limit_per_customer')
            ? Number(field(form, 'usage_limit_per_customer'))
            : null,
          is_active: form.get('is_active') === 'on',
        };
        return save.mutateAsync(
          coupon ? { id: coupon.id, body } : { body: { ...body, code: field(form, 'code') } },
        );
      }}
    >
      {!coupon && (
        <FormField label="Code" required hint="Letters and numbers, e.g. FESTIVE10">
          <Input name="code" required className="uppercase" maxLength={40} />
        </FormField>
      )}
      <FormField label="Description" hint="Shown to staff">
        <Input name="description" defaultValue={coupon?.description ?? ''} />
      </FormField>
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="Type">
          <Select name="kind" defaultValue={coupon?.kind ?? 'percent'}>
            <option value="percent">% off</option>
            <option value="flat">₹ off</option>
          </Select>
        </FormField>
        <FormField label="Value" required>
          <Input name="value" required inputMode="decimal" defaultValue={coupon?.value} />
        </FormField>
        <FormField label="Maximum discount (₹)" hint="Optional cap for % coupons">
          <Input
            name="max_discount_amount"
            inputMode="decimal"
            defaultValue={coupon?.max_discount_amount ?? ''}
          />
        </FormField>
        <FormField label="Minimum order (₹)" hint="Optional">
          <Input
            name="min_order_amount"
            inputMode="decimal"
            defaultValue={coupon?.min_order_amount ?? ''}
          />
        </FormField>
        <FormField label="Total uses" hint="Optional">
          <Input
            name="usage_limit_total"
            inputMode="numeric"
            defaultValue={coupon?.usage_limit_total ?? ''}
          />
        </FormField>
        <FormField label="Uses per customer" hint="Optional">
          <Input
            name="usage_limit_per_customer"
            inputMode="numeric"
            defaultValue={coupon?.usage_limit_per_customer ?? ''}
          />
        </FormField>
        <FormField label="Starts" required>
          <Input
            name="starts_at"
            type="datetime-local"
            required
            defaultValue={toLocalInput(coupon?.starts_at) || nowLocal()}
          />
        </FormField>
        <FormField label="Ends" hint="Optional">
          <Input
            name="ends_at"
            type="datetime-local"
            defaultValue={toLocalInput(coupon?.ends_at)}
          />
        </FormField>
      </div>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          name="is_active"
          defaultChecked={coupon?.is_active ?? true}
          className="size-4 accent-ink"
        />{' '}
        Active
      </label>
    </FormDialog>
  );
}

export function AdminPromotionsPage() {
  const discounts = useDiscounts();
  const coupons = useCoupons();
  return (
    <AdminPage title="Discounts & coupons">
      <div className="space-y-6">
        <Panel title="Automatic discounts" actions={<DiscountDialog />}>
          <DataTable
            caption="Automatic discounts"
            rows={discounts.data}
            rowKey={(d) => d.id}
            loading={discounts.isPending}
            error={discounts.error}
            columns={[
              { header: 'Name', cell: (d) => d.name },
              {
                header: 'Offer',
                cell: (d) => `${d.value} ${DISCOUNT_KINDS[d.kind as keyof typeof DISCOUNT_KINDS]}`,
              },
              { header: 'Applies to', cell: (d) => d.scope_name ?? 'Everything' },
              {
                header: 'When',
                cell: (d) =>
                  `${formatDateTime(d.starts_at)}${d.ends_at ? ` – ${formatDateTime(d.ends_at)}` : ''}`,
              },
              {
                header: 'Status',
                cell: (d) =>
                  d.running_now ? <Badge tone="success">running</Badge> : <Badge>off</Badge>,
              },
              { header: '', cell: (d) => <DiscountDialog discount={d} /> },
            ]}
          />
        </Panel>
        <Panel title="Coupons" actions={<CouponDialog />}>
          <DataTable
            caption="Coupons"
            rows={coupons.data}
            rowKey={(c) => c.id}
            loading={coupons.isPending}
            error={coupons.error}
            columns={[
              { header: 'Code', cell: (c) => <span className="font-medium">{c.code}</span> },
              {
                header: 'Offer',
                cell: (c) =>
                  c.kind === 'percent'
                    ? `${c.value}%${c.max_discount_amount ? ` up to ${formatMoney(c.max_discount_amount)}` : ''}`
                    : formatMoney(c.value),
              },
              {
                header: 'Min. order',
                cell: (c) => (c.min_order_amount ? formatMoney(c.min_order_amount) : '—'),
              },
              {
                header: 'Used',
                cell: (c) => `${String(c.times_used)} (+${String(c.times_reserved)} pending)`,
              },
              {
                header: 'Status',
                cell: (c) => (c.is_active ? 'Active' : 'Off') + (c.is_sample ? ' · sample' : ''),
              },
              { header: '', cell: (c) => <CouponDialog coupon={c} /> },
            ]}
          />
        </Panel>
      </div>
    </AdminPage>
  );
}

// --------------------------------------------------------------------------- shipping

function MethodDialog({ method }: { method?: ShippingMethod }) {
  const save = useSaveShippingMethod();
  return (
    <FormDialog
      title={method ? `Edit ${method.name}` : 'New delivery method'}
      submitLabel="Save"
      trigger={(open) =>
        method ? (
          <Button size="sm" variant="ghost" onClick={open}>
            Edit
          </Button>
        ) : (
          <Button size="sm" variant="secondary" onClick={open}>
            <Plus className="size-4" aria-hidden="true" /> New method
          </Button>
        )
      }
      onSubmit={(form) =>
        save.mutateAsync({
          id: method?.id,
          body: {
            code: field(form, 'code'),
            name: field(form, 'name'),
            description: opt(field(form, 'description')),
            fee: field(form, 'fee'),
            free_above: opt(field(form, 'free_above')),
            min_days: Number(field(form, 'min_days')),
            max_days: Number(field(form, 'max_days')),
            is_active: form.get('is_active') === 'on',
            sort_order: Number(field(form, 'sort_order') || 0),
          },
        })
      }
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="Code" required hint="lowercase, e.g. standard">
          <Input name="code" required defaultValue={method?.code} />
        </FormField>
        <FormField label="Name" required>
          <Input name="name" required defaultValue={method?.name} />
        </FormField>
        <FormField label="Fee (₹)" required>
          <Input name="fee" required inputMode="decimal" defaultValue={method?.fee ?? '0'} />
        </FormField>
        <FormField label="Free above (₹)" hint="Optional">
          <Input name="free_above" inputMode="decimal" defaultValue={method?.free_above ?? ''} />
        </FormField>
        <FormField label="Min. days" required>
          <Input
            name="min_days"
            required
            inputMode="numeric"
            defaultValue={method?.min_days ?? 3}
          />
        </FormField>
        <FormField label="Max. days" required>
          <Input
            name="max_days"
            required
            inputMode="numeric"
            defaultValue={method?.max_days ?? 7}
          />
        </FormField>
        <FormField label="Order">
          <Input name="sort_order" inputMode="numeric" defaultValue={method?.sort_order ?? 0} />
        </FormField>
      </div>
      <FormField label="Description">
        <Input name="description" defaultValue={method?.description ?? ''} />
      </FormField>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          name="is_active"
          defaultChecked={method?.is_active ?? true}
          className="size-4 accent-ink"
        />{' '}
        Offered at checkout
      </label>
    </FormDialog>
  );
}

function ZoneDialog({ zone }: { zone?: ShippingZone }) {
  const save = useSaveShippingZone();
  return (
    <FormDialog
      title={zone ? `Edit ${zone.name}` : 'New delivery zone'}
      description="If any zones exist, only PIN codes starting with one of their prefixes can order."
      submitLabel="Save zone"
      trigger={(open) =>
        zone ? (
          <Button size="sm" variant="ghost" onClick={open}>
            Edit
          </Button>
        ) : (
          <Button size="sm" variant="secondary" onClick={open}>
            <Plus className="size-4" aria-hidden="true" /> New zone
          </Button>
        )
      }
      onSubmit={(form) =>
        save.mutateAsync({
          id: zone?.id,
          body: {
            name: field(form, 'name'),
            pincode_prefixes: field(form, 'prefixes')
              .split(/[\s,]+/)
              .filter(Boolean),
            extra_days: Number(field(form, 'extra_days') || 0),
            is_active: form.get('is_active') === 'on',
          },
        })
      }
    >
      <FormField label="Name" required>
        <Input name="name" required defaultValue={zone?.name} />
      </FormField>
      <FormField
        label="PIN codes or prefixes"
        required
        hint="Separated by spaces or commas, e.g. 56 57 110001"
      >
        <Textarea
          name="prefixes"
          rows={3}
          required
          defaultValue={zone?.pincode_prefixes.join(' ')}
        />
      </FormField>
      <FormField label="Extra delivery days">
        <Input name="extra_days" inputMode="numeric" defaultValue={zone?.extra_days ?? 0} />
      </FormField>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          name="is_active"
          defaultChecked={zone?.is_active ?? true}
          className="size-4 accent-ink"
        />{' '}
        Active
      </label>
    </FormDialog>
  );
}

export function AdminShippingPage() {
  const methods = useShippingMethods();
  const zones = useShippingZones();
  const deleteZone = useDeleteShippingZone();
  return (
    <AdminPage
      title="Delivery"
      description="Delivery methods and fees shown at checkout, and the PIN codes you deliver to."
    >
      <div className="space-y-6">
        <Panel title="Delivery methods" actions={<MethodDialog />}>
          <DataTable
            caption="Delivery methods"
            rows={methods.data}
            rowKey={(m) => m.id}
            loading={methods.isPending}
            error={methods.error}
            columns={[
              { header: 'Name', cell: (m) => `${m.name} (${m.code})` },
              {
                header: 'Fee',
                cell: (m) =>
                  `${formatMoney(m.fee)}${m.free_above ? `, free above ${formatMoney(m.free_above)}` : ''}`,
              },
              { header: 'Days', cell: (m) => `${String(m.min_days)}–${String(m.max_days)}` },
              { header: 'Status', cell: (m) => (m.is_active ? 'Offered' : 'Off') },
              { header: '', cell: (m) => <MethodDialog method={m} /> },
            ]}
          />
        </Panel>
        <Panel title="Delivery zones" actions={<ZoneDialog />}>
          {zones.data?.length === 0 && (
            <p className="mb-3 text-sm text-ink-muted">
              No zones: every valid Indian PIN code can order.
            </p>
          )}
          <DataTable
            caption="Delivery zones"
            rows={zones.data}
            rowKey={(z) => z.id}
            loading={zones.isPending}
            error={zones.error}
            empty="No zones."
            columns={[
              { header: 'Name', cell: (z) => z.name },
              {
                header: 'Prefixes',
                cell: (z) => <span className="break-all">{z.pincode_prefixes.join(', ')}</span>,
              },
              { header: 'Extra days', cell: (z) => z.extra_days },
              { header: 'Status', cell: (z) => (z.is_active ? 'Active' : 'Off') },
              {
                header: '',
                cell: (z) => (
                  <div className="flex gap-1">
                    <ZoneDialog zone={z} />
                    <Button
                      size="sm"
                      variant="ghost"
                      aria-label={`Delete zone ${z.name}`}
                      onClick={() => {
                        deleteZone.mutate(z.id);
                      }}
                    >
                      <Trash2 className="size-4" aria-hidden="true" />
                    </Button>
                  </div>
                ),
              },
            ]}
          />
        </Panel>
      </div>
    </AdminPage>
  );
}

// --------------------------------------------------------------------------- content

function PageEditor({ page }: { page: ContentPageAdmin }) {
  const save = useSaveContentPage();
  const { notify } = useToast();
  const [title, setTitle] = useState(page.title);
  const [summary, setSummary] = useState(page.summary ?? '');
  const [body, setBody] = useState(page.body_markdown);
  const [draft, setDraft] = useState(page.is_draft_template);
  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        save.mutate(
          {
            slug: page.slug,
            body: {
              title,
              summary: summary || null,
              body_markdown: body,
              is_draft_template: draft,
            },
          },
          {
            onSuccess: () => {
              notify('Page saved.', 'success');
            },
          },
        );
      }}
    >
      {save.isError && <Alert tone="danger" title={errorMessage(save.error)} />}
      <FormField label="Title" required>
        <Input
          value={title}
          maxLength={160}
          onChange={(e) => {
            setTitle(e.target.value);
          }}
        />
      </FormField>
      <FormField label="Summary">
        <Input
          value={summary}
          maxLength={300}
          onChange={(e) => {
            setSummary(e.target.value);
          }}
        />
      </FormField>
      <div className="grid gap-4 lg:grid-cols-2">
        <FormField label="Text" hint="Markdown: # Heading, **bold**, - list. HTML is not allowed.">
          <Textarea
            rows={18}
            className="font-mono text-sm"
            value={body}
            onChange={(e) => {
              setBody(e.target.value);
            }}
          />
        </FormField>
        <div>
          <p className="mb-1.5 text-sm font-medium">Preview</p>
          <div className="prose-store max-h-[28rem] overflow-y-auto rounded-sm border border-line bg-surface p-4 text-sm">
            <Suspense fallback={<Skeleton className="h-40" />}>
              <Markdown>{body}</Markdown>
            </Suspense>
          </div>
        </div>
      </div>
      <label className="flex items-start gap-2 text-sm">
        <input
          type="checkbox"
          className="mt-0.5 size-4 accent-ink"
          checked={draft}
          onChange={(e) => {
            setDraft(e.target.checked);
          }}
        />
        Still a template awaiting review (customers see a “draft” notice). Untick only after the
        text is checked — policies by a legal professional.
      </label>
      <Button type="submit" loading={save.isPending}>
        Save page
      </Button>
    </form>
  );
}

export function AdminContentPage() {
  const pages = useContentPages();
  const [slug, setSlug] = useState<string | null>(null);
  const selected = pages.data?.find((p) => p.slug === (slug ?? pages.data[0]?.slug));
  return (
    <AdminPage title="Content pages" description="About, FAQ, guides and policies.">
      {pages.isPending ? (
        <Skeleton className="h-64" />
      ) : pages.isError ? (
        <ErrorState error={pages.error} onRetry={() => void pages.refetch()} />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[16rem_1fr]">
          <nav aria-label="Pages">
            <ul className="space-y-1">
              {pages.data.map((p) => (
                <li key={p.slug}>
                  <button
                    type="button"
                    aria-current={selected?.slug === p.slug ? 'page' : undefined}
                    className="w-full rounded-sm px-3 py-2 text-left text-sm hover:bg-surface-muted aria-[current=page]:bg-ink aria-[current=page]:text-ivory"
                    onClick={() => {
                      setSlug(p.slug);
                    }}
                  >
                    {p.title}
                    {p.is_draft_template && (
                      <span className="block text-xs opacity-75">template</span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          </nav>
          {selected && (
            <Panel title={`/${selected.slug}`}>
              <PageEditor key={selected.slug} page={selected} />
            </Panel>
          )}
        </div>
      )}
    </AdminPage>
  );
}

// --------------------------------------------------------------------------- settings

export function AdminSettingsPage() {
  const settings = useAdminSettings();
  const save = useSaveSettings();
  const { notify } = useToast();
  const saved = () => {
    notify('Settings saved.', 'success');
  };
  if (settings.isPending) return <Skeleton className="h-96" />;
  if (settings.isError)
    return <ErrorState error={settings.error} onRetry={() => void settings.refetch()} />;
  const s = settings.data;
  return (
    <AdminPage
      title="Settings"
      description="Business details shown on the site, the announcement bar, GST rates and gold-rate safety rules."
    >
      {save.isError && <Alert tone="danger" title={errorMessage(save.error)} className="mb-4" />}
      <div className="space-y-6">
        <Panel title="Store details">
          <p className="mb-4 text-sm text-ink-muted">
            Values in [square brackets] are placeholders and are shown to customers as such. Replace
            them with your real, verified details.
          </p>
          <form
            className="grid gap-4 sm:grid-cols-2"
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              save.mutate(
                {
                  group: 'store',
                  body: {
                    tagline: field(f, 'tagline'),
                    support_email: field(f, 'support_email'),
                    support_phone: field(f, 'support_phone'),
                    whatsapp: opt(field(f, 'whatsapp')),
                    business_address: field(f, 'business_address'),
                    gstin: field(f, 'gstin'),
                    business_hours: field(f, 'business_hours'),
                  },
                },
                { onSuccess: saved },
              );
            }}
          >
            <FormField label="Tagline">
              <Input name="tagline" defaultValue={s.store.tagline} />
            </FormField>
            <FormField label="Support email">
              <Input name="support_email" defaultValue={s.store.support_email} />
            </FormField>
            <FormField label="Support phone">
              <Input name="support_phone" defaultValue={s.store.support_phone} />
            </FormField>
            <FormField label="WhatsApp" hint="Optional">
              <Input name="whatsapp" defaultValue={s.store.whatsapp ?? ''} />
            </FormField>
            <FormField label="GSTIN">
              <Input name="gstin" defaultValue={s.store.gstin} />
            </FormField>
            <FormField label="Business hours">
              <Input name="business_hours" defaultValue={s.store.business_hours} />
            </FormField>
            <FormField label="Business address" className="sm:col-span-2">
              <Textarea name="business_address" rows={2} defaultValue={s.store.business_address} />
            </FormField>
            <div>
              <Button type="submit" loading={save.isPending}>
                Save store details
              </Button>
            </div>
          </form>
        </Panel>
        <Panel title="Announcement bar">
          <form
            className="grid gap-4 sm:grid-cols-2"
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              save.mutate(
                {
                  group: 'announcement',
                  body: {
                    enabled: f.get('enabled') === 'on',
                    text: field(f, 'text'),
                    link: opt(field(f, 'link')),
                  },
                },
                { onSuccess: saved },
              );
            }}
          >
            <FormField label="Text">
              <Input name="text" maxLength={160} defaultValue={s.announcement.text} />
            </FormField>
            <FormField label="Link" hint="A site path like /collections, or https://…">
              <Input name="link" defaultValue={s.announcement.link ?? ''} />
            </FormField>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                name="enabled"
                defaultChecked={s.announcement.enabled}
                className="size-4 accent-ink"
              />{' '}
              Show the bar
            </label>
            <div>
              <Button type="submit" loading={save.isPending}>
                Save announcement
              </Button>
            </div>
          </form>
        </Panel>
        <Panel title="GST rates">
          <Alert tone="warning" className="mb-4">
            Confirm these rates with a tax professional. Changing them changes every price
            immediately; existing orders keep the rates they were placed with.
          </Alert>
          <form
            className="grid gap-4 sm:grid-cols-4"
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              save.mutate(
                {
                  group: 'tax',
                  body: {
                    metal_percent: field(f, 'metal_percent'),
                    making_percent: field(f, 'making_percent'),
                    stones_percent: field(f, 'stones_percent'),
                    shipping_percent: field(f, 'shipping_percent'),
                  },
                },
                { onSuccess: saved },
              );
            }}
          >
            {(
              [
                ['metal_percent', 'Gold / product value %'],
                ['making_percent', 'Making charges %'],
                ['stones_percent', 'Stones & other %'],
                ['shipping_percent', 'Shipping %'],
              ] as const
            ).map(([name, label]) => (
              <FormField key={name} label={label}>
                <Input name={name} inputMode="decimal" defaultValue={s.tax[name]} />
              </FormField>
            ))}
            <div className="sm:col-span-4">
              <Button type="submit" loading={save.isPending}>
                Save GST rates
              </Button>
            </div>
          </form>
        </Panel>
        <Panel title="Gold-rate safety">
          <form
            className="grid gap-4 sm:grid-cols-3"
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              save.mutate(
                {
                  group: 'pricing-policy',
                  body: {
                    gold_rate_max_change_percent: field(f, 'max'),
                    gold_rate_stale_after_hours: Number(field(f, 'stale')),
                    block_checkout_when_rate_stale: f.get('block') === 'on',
                  },
                },
                { onSuccess: saved },
              );
            }}
          >
            <FormField label="Confirm changes larger than (%)">
              <Input
                name="max"
                inputMode="decimal"
                defaultValue={s.pricing_policy.gold_rate_max_change_percent}
              />
            </FormField>
            <FormField label="Warn when a rate is older than (hours)">
              <Input
                name="stale"
                inputMode="numeric"
                defaultValue={s.pricing_policy.gold_rate_stale_after_hours}
              />
            </FormField>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                name="block"
                defaultChecked={s.pricing_policy.block_checkout_when_rate_stale}
                className="size-4 accent-ink"
              />
              Pause checkout of weight-priced pieces while the rate is stale
            </label>
            <div className="sm:col-span-3">
              <Button type="submit" loading={save.isPending}>
                Save
              </Button>
            </div>
          </form>
        </Panel>
      </div>
    </AdminPage>
  );
}

// --------------------------------------------------------------------------- staff

export function AdminStaffPage() {
  const users = useStaffUsers();
  const act = useStaffAction();
  const me = useMe();
  const { notify } = useToast();
  const onError = (e: unknown) => {
    notify(errorMessage(e), 'error');
  };
  return (
    <AdminPage
      title="Staff"
      description="Staff can manage orders, products, stock, customers and content. Admins can also refund, change prices, settings and staff. People sign up for an account first; then you give them access here."
      actions={
        <FormDialog
          title="Give someone access"
          submitLabel="Give access"
          trigger={(open) => (
            <Button onClick={open}>
              <Plus className="size-4" aria-hidden="true" /> Add staff
            </Button>
          )}
          onSubmit={(form) =>
            act.mutateAsync({
              kind: 'promote',
              email: field(form, 'email'),
              role: field(form, 'role') as 'staff' | 'admin',
            })
          }
        >
          <FormField label="Their account email" required>
            <Input name="email" type="email" required />
          </FormField>
          <FormField label="Role">
            <Select name="role" defaultValue="staff">
              <option value="staff">Staff</option>
              <option value="admin">Admin</option>
            </Select>
          </FormField>
        </FormDialog>
      }
    >
      <DataTable
        caption="Staff accounts"
        rows={users.data}
        rowKey={(u) => u.id}
        loading={users.isPending}
        error={users.error}
        columns={[
          {
            header: 'Name',
            cell: (u) => (
              <>
                {u.full_name}
                <span className="block text-xs text-ink-muted">{u.email}</span>
              </>
            ),
          },
          {
            header: 'Role',
            cell: (u) => (
              <Select
                aria-label={`Role of ${u.full_name}`}
                className="w-36"
                value={u.role}
                disabled={u.id === me.data?.id || act.isPending}
                onChange={(e) => {
                  act.mutate(
                    {
                      kind: 'role',
                      id: u.id,
                      role: e.target.value as 'customer' | 'staff' | 'admin',
                    },
                    { onError },
                  );
                }}
              >
                <option value="staff">Staff</option>
                <option value="admin">Admin</option>
                <option value="customer">No access</option>
              </Select>
            ),
          },
          {
            header: 'Last sign-in',
            cell: (u) => (u.last_login_at ? formatDateTime(u.last_login_at) : 'Never'),
          },
          {
            header: 'Account',
            cell: (u) =>
              u.id === me.data?.id ? (
                'You'
              ) : (
                <Button
                  size="sm"
                  variant={u.is_active ? 'ghost' : 'secondary'}
                  onClick={() => {
                    act.mutate({ kind: 'active', id: u.id, is_active: !u.is_active }, { onError });
                  }}
                >
                  {u.is_active ? 'Deactivate' : 'Reactivate'}
                </Button>
              ),
          },
        ]}
      />
    </AdminPage>
  );
}
