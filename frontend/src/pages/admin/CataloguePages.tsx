import { ArrowDown, ArrowUp, ImagePlus, Plus, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useFieldArray, useForm, useWatch, type UseFormRegister } from 'react-hook-form';
import { Link, useNavigate, useParams } from 'react-router';

import { ApiError } from '@/api/client';
import {
  useAddVariant,
  useAdminCategories,
  useAdminCollections,
  useAdminProduct,
  useAdminProducts,
  useCreateProduct,
  useDeleteCategory,
  useImageAction,
  usePricePreview,
  useSaveCategory,
  useSaveCollection,
  useUpdateProduct,
  useUpdateVariant,
  useUploadImage,
  type AdminCategory,
  type AdminCollection,
  type AdminProduct,
  type ProductCreateInput,
  type ProductInput,
  type VariantInput,
} from '@/api/queries/admin';
import {
  AdminPage,
  DataTable,
  FormDialog,
  Pager,
  Panel,
  field,
  usePageParam,
} from '@/components/admin/AdminUI';
import { PriceSummary } from '@/components/orders/PriceSummary';
import { ProductImage } from '@/components/product/ProductImage';
import { Button } from '@/components/ui/Button';
import { Alert, Badge, ErrorState, Skeleton } from '@/components/ui/Feedback';
import { FormField, Input, Select, Textarea } from '@/components/ui/Field';
import { useToast } from '@/components/ui/Toaster';
import { formatDateTime, formatMoney, hasPaise } from '@/lib/format';
import { errorMessage } from '@/lib/forms';

const STATUS_TONE = { draft: 'neutral', active: 'success', archived: 'warning' } as const;

function opt(value: string): string | null {
  return value.trim() === '' ? null : value.trim();
}

// --------------------------------------------------------------------------- product list

export function AdminProductsPage() {
  const [page, setPage] = usePageParam();
  const [q, setQ] = useState('');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const products = useAdminProducts({ q: search, status, page });
  return (
    <AdminPage
      title="Products"
      actions={
        <Button asChild>
          <Link to="/admin/products/new">
            <Plus className="size-4" aria-hidden="true" /> New product
          </Link>
        </Button>
      }
    >
      <form
        className="mb-4 flex flex-wrap items-end gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          setSearch(q);
          setPage(1);
        }}
      >
        <FormField label="Search" hint="Name or SKU" className="min-w-56 flex-1">
          <Input
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
            }}
          />
        </FormField>
        <FormField label="Status" className="w-40">
          <Select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All</option>
            <option value="active">Active</option>
            <option value="draft">Draft</option>
            <option value="archived">Archived</option>
          </Select>
        </FormField>
        <Button type="submit" variant="secondary">
          Search
        </Button>
      </form>
      <DataTable
        caption="Products"
        rows={products.data?.items}
        rowKey={(p) => p.id}
        loading={products.isPending}
        error={products.error}
        columns={[
          {
            header: 'Product',
            cell: (p) => (
              <div className="flex items-center gap-3">
                <div className="w-12 shrink-0 overflow-hidden rounded-sm bg-surface-muted">
                  {p.image && (
                    <ProductImage
                      image={p.image}
                      sizes="48px"
                      className="aspect-4/5 w-full object-cover"
                    />
                  )}
                </div>
                <div>
                  <Link
                    to={`/admin/products/${p.id}`}
                    className="font-medium underline-offset-4 hover:underline"
                  >
                    {p.name}
                  </Link>
                  <span className="block text-xs text-ink-muted">
                    {p.category} · {p.purity} ·{' '}
                    {p.pricing_model === 'weight_based' ? 'by weight' : 'fixed price'}
                    {p.is_sample ? ' · sample' : ''}
                  </span>
                </div>
              </div>
            ),
          },
          { header: 'Status', cell: (p) => <Badge tone={STATUS_TONE[p.status]}>{p.status}</Badge> },
          { header: 'Variants', cell: (p) => p.variant_count, className: 'text-right' },
          { header: 'Available', cell: (p) => p.available, className: 'text-right' },
          {
            header: 'From',
            cell: (p) => (p.price_from ? formatMoney(p.price_from) : '—'),
            className: 'text-right tabular',
          },
          { header: 'Updated', cell: (p) => formatDateTime(p.updated_at) },
        ]}
      />
      {products.data && (
        <Pager
          page={page}
          pages={products.data.pages}
          total={products.data.total}
          onChange={setPage}
        />
      )}
    </AdminPage>
  );
}

// --------------------------------------------------------------------------- product form

interface VariantForm {
  sku: string;
  label: string;
  size: string;
  gross_weight_g: string;
  net_gold_weight_g: string;
  stone_weight_ct: string;
  stone_value: string;
  other_charges: string;
  fixed_price: string;
  huid: string;
  initial_stock: string;
}

interface ProductForm {
  name: string;
  slug: string;
  category_id: string;
  status: 'draft' | 'active' | 'archived';
  metal_colour: 'yellow' | 'white' | 'rose' | 'two_tone';
  purity: '24K' | '22K' | '18K' | '14K';
  pricing_model: 'fixed' | 'weight_based';
  making_charge_type: 'per_gram' | 'percent' | 'flat' | 'none';
  making_charge_value: string;
  wastage_percent: string;
  description: string;
  stone_details: string;
  hallmark_details: string;
  certification_details: string;
  care_instructions: string;
  return_eligible: boolean;
  exchange_eligible: boolean;
  return_window_days: string;
  is_featured: boolean;
  is_bestseller: boolean;
  seo_title: string;
  seo_description: string;
  attributes: string;
  collection_ids: string[];
  variants: VariantForm[];
}

const EMPTY_VARIANT: VariantForm = {
  sku: '',
  label: 'Standard',
  size: '',
  gross_weight_g: '',
  net_gold_weight_g: '',
  stone_weight_ct: '',
  stone_value: '0',
  other_charges: '0',
  fixed_price: '',
  huid: '',
  initial_stock: '0',
};

function toForm(p?: AdminProduct): ProductForm {
  return {
    name: p?.name ?? '',
    slug: p?.slug ?? '',
    category_id: p?.category_id ?? '',
    status: p?.status ?? 'draft',
    metal_colour: p?.metal_colour ?? 'yellow',
    purity: p?.purity ?? '22K',
    pricing_model: p?.pricing_model ?? 'weight_based',
    making_charge_type: p?.making_charge_type ?? 'percent',
    making_charge_value: p?.making_charge_value ?? '0',
    wastage_percent: p?.wastage_percent ?? '',
    description: p?.description ?? '',
    stone_details: p?.stone_details ?? '',
    hallmark_details: p?.hallmark_details ?? '',
    certification_details: p?.certification_details ?? '',
    care_instructions: p?.care_instructions ?? '',
    return_eligible: p?.return_eligible ?? false,
    exchange_eligible: p?.exchange_eligible ?? false,
    return_window_days: p?.return_window_days?.toString() ?? '',
    is_featured: p?.is_featured ?? false,
    is_bestseller: p?.is_bestseller ?? false,
    seo_title: p?.seo_title ?? '',
    seo_description: p?.seo_description ?? '',
    attributes: (p?.attributes ?? []).map((a) => `${a.key}: ${a.value}`).join('\n'),
    collection_ids: p?.collection_ids ?? [],
    variants: p ? [] : [{ ...EMPTY_VARIANT }],
  };
}

function variantBody(v: VariantForm): VariantInput {
  return {
    sku: v.sku.trim().toUpperCase(),
    label: v.label.trim() || 'Standard',
    size: opt(v.size),
    gross_weight_g: opt(v.gross_weight_g),
    net_gold_weight_g: opt(v.net_gold_weight_g),
    stone_weight_ct: opt(v.stone_weight_ct),
    stone_value: opt(v.stone_value) ?? '0',
    other_charges: opt(v.other_charges) ?? '0',
    fixed_price: opt(v.fixed_price),
    huid: opt(v.huid),
    is_active: true,
    is_default: false,
    sort_order: 0,
  };
}

function productBody(f: ProductForm): ProductInput {
  return {
    name: f.name.trim(),
    slug: opt(f.slug),
    category_id: f.category_id,
    status: f.status,
    metal_colour: f.metal_colour,
    purity: f.purity,
    pricing_model: f.pricing_model,
    making_charge_type: f.making_charge_type,
    making_charge_value: opt(f.making_charge_value) ?? '0',
    wastage_percent: opt(f.wastage_percent),
    description: opt(f.description),
    stone_details: opt(f.stone_details),
    hallmark_details: opt(f.hallmark_details),
    certification_details: opt(f.certification_details),
    care_instructions: opt(f.care_instructions),
    return_eligible: f.return_eligible,
    exchange_eligible: f.exchange_eligible,
    return_window_days: f.return_window_days ? Number(f.return_window_days) : null,
    is_featured: f.is_featured,
    is_bestseller: f.is_bestseller,
    seo_title: opt(f.seo_title),
    seo_description: opt(f.seo_description),
    attributes: f.attributes
      .split('\n')
      .map((line) => line.split(':'))
      .filter((parts) => parts.length >= 2 && parts[0]?.trim() && parts.slice(1).join(':').trim())
      .map(([key = '', ...rest]) => ({ key: key.trim(), value: rest.join(':').trim() })),
    collection_ids: f.collection_ids,
  };
}

function VariantFields({
  register,
  prefix,
  withStock,
}: {
  register: UseFormRegister<ProductForm>;
  prefix: `variants.${number}`;
  withStock: boolean;
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-4">
      <FormField label="SKU" required>
        <Input {...register(`${prefix}.sku`)} className="uppercase" />
      </FormField>
      <FormField label="Label" hint="e.g. Size 12">
        <Input {...register(`${prefix}.label`)} />
      </FormField>
      <FormField label="Size">
        <Input {...register(`${prefix}.size`)} />
      </FormField>
      <FormField label="Net gold weight (g)">
        <Input inputMode="decimal" {...register(`${prefix}.net_gold_weight_g`)} />
      </FormField>
      <FormField label="Gross weight (g)">
        <Input inputMode="decimal" {...register(`${prefix}.gross_weight_g`)} />
      </FormField>
      <FormField label="Fixed price before GST (₹)" hint="Fixed-price products only">
        <Input inputMode="decimal" {...register(`${prefix}.fixed_price`)} />
      </FormField>
      <FormField label="Stone value (₹)">
        <Input inputMode="decimal" {...register(`${prefix}.stone_value`)} />
      </FormField>
      <FormField label="Other charges (₹)">
        <Input inputMode="decimal" {...register(`${prefix}.other_charges`)} />
      </FormField>
      <FormField label="Stone weight (ct)">
        <Input inputMode="decimal" {...register(`${prefix}.stone_weight_ct`)} />
      </FormField>
      <FormField label="HUID" hint="If recorded">
        <Input {...register(`${prefix}.huid`)} className="uppercase" maxLength={6} />
      </FormField>
      {withStock && (
        <FormField label="Initial stock">
          <Input inputMode="numeric" {...register(`${prefix}.initial_stock`)} />
        </FormField>
      )}
    </div>
  );
}

function ServerErrors({ error }: { error: unknown }) {
  if (!error) return null;
  const fields = error instanceof ApiError ? Object.entries(error.fieldErrors) : [];
  return (
    <Alert tone="danger" title={errorMessage(error)}>
      {fields.length > 0 && (
        <ul className="list-disc pl-5">
          {fields.map(([name, message]) => (
            <li key={name}>
              <span className="font-medium">{name.replaceAll('_', ' ')}</span>: {message}
            </li>
          ))}
        </ul>
      )}
    </Alert>
  );
}

function PricePreviewPanel({ form }: { form: ProductForm }) {
  const preview = usePricePreview();
  const variants = form.variants.length ? form.variants : [EMPTY_VARIANT];
  return (
    <Panel title="Price preview">
      <p className="mb-3 text-sm text-ink-muted">
        What customers would pay today with these inputs (current gold rate and GST; automatic
        discounts and coupons not included). Nothing is saved.
      </p>
      <Button
        type="button"
        variant="secondary"
        loading={preview.isPending}
        onClick={() => {
          preview.mutate({
            purity: form.purity,
            pricing_model: form.pricing_model,
            making_charge_type: form.making_charge_type,
            making_charge_value: opt(form.making_charge_value) ?? '0',
            wastage_percent: opt(form.wastage_percent),
            variants: variants.map((v) => ({
              label: v.label || v.sku || 'Variant',
              net_gold_weight_g: opt(v.net_gold_weight_g),
              fixed_price: opt(v.fixed_price),
              stone_value: opt(v.stone_value) ?? '0',
              other_charges: opt(v.other_charges) ?? '0',
            })),
          });
        }}
      >
        Calculate prices
      </Button>
      {preview.isError && (
        <Alert tone="danger" title={errorMessage(preview.error)} className="mt-3" />
      )}
      {preview.data && (
        <div className="mt-4 space-y-4">
          {preview.data.gold_rate_per_gram && (
            <p className="text-sm">
              Gold rate used: {formatMoney(preview.data.gold_rate_per_gram, { paise: true })}/g
            </p>
          )}
          {preview.data.variants.map((v) => (
            <div key={v.label}>
              <p className="text-sm font-medium">{v.label}</p>
              {v.error ? (
                <p className="text-sm text-danger">{v.error}</p>
              ) : (
                <PriceSummary rows={v.breakdown} caption={`Price of ${v.label}`} />
              )}
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function VariantsEditor({ product }: { product: AdminProduct }) {
  const update = useUpdateVariant();
  const add = useAddVariant();
  const { notify } = useToast();

  const variantFields = (v?: AdminProduct['variants'][number]) => (
    <div className="grid gap-3 sm:grid-cols-2">
      <FormField label="SKU" required>
        <Input name="sku" required defaultValue={v?.sku} className="uppercase" />
      </FormField>
      <FormField label="Label">
        <Input name="label" defaultValue={v?.label ?? 'Standard'} />
      </FormField>
      <FormField label="Size">
        <Input name="size" defaultValue={v?.size ?? ''} />
      </FormField>
      <FormField label="Net gold weight (g)">
        <Input
          name="net_gold_weight_g"
          inputMode="decimal"
          defaultValue={v?.net_gold_weight_g ?? ''}
        />
      </FormField>
      <FormField label="Gross weight (g)">
        <Input name="gross_weight_g" inputMode="decimal" defaultValue={v?.gross_weight_g ?? ''} />
      </FormField>
      <FormField label="Fixed price before GST (₹)">
        <Input name="fixed_price" inputMode="decimal" defaultValue={v?.fixed_price ?? ''} />
      </FormField>
      <FormField label="Stone value (₹)">
        <Input name="stone_value" inputMode="decimal" defaultValue={v?.stone_value ?? '0'} />
      </FormField>
      <FormField label="Other charges (₹)">
        <Input name="other_charges" inputMode="decimal" defaultValue={v?.other_charges ?? '0'} />
      </FormField>
      <FormField label="HUID">
        <Input name="huid" maxLength={6} defaultValue={v?.huid ?? ''} className="uppercase" />
      </FormField>
      {!v && (
        <FormField label="Initial stock">
          <Input name="initial_stock" inputMode="numeric" defaultValue="0" />
        </FormField>
      )}
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          name="is_active"
          defaultChecked={v?.is_active ?? true}
          className="size-4 accent-ink"
        />{' '}
        Active
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          name="is_default"
          defaultChecked={v?.is_default ?? false}
          className="size-4 accent-ink"
        />{' '}
        Default
      </label>
    </div>
  );

  const fromForm = (form: FormData): VariantInput => ({
    ...variantBody({
      ...EMPTY_VARIANT,
      sku: field(form, 'sku'),
      label: field(form, 'label'),
      size: field(form, 'size'),
      net_gold_weight_g: field(form, 'net_gold_weight_g'),
      gross_weight_g: field(form, 'gross_weight_g'),
      fixed_price: field(form, 'fixed_price'),
      stone_value: field(form, 'stone_value'),
      other_charges: field(form, 'other_charges'),
      huid: field(form, 'huid'),
    }),
    is_active: form.get('is_active') === 'on',
    is_default: form.get('is_default') === 'on',
  });

  return (
    <Panel
      title="Variants"
      actions={
        <FormDialog
          title="Add a variant"
          submitLabel="Add variant"
          trigger={(open) => (
            <Button size="sm" variant="secondary" onClick={open}>
              <Plus className="size-4" aria-hidden="true" /> Add variant
            </Button>
          )}
          onSubmit={(form) =>
            add
              .mutateAsync({
                id: product.id,
                body: {
                  ...fromForm(form),
                  initial_stock: Number(field(form, 'initial_stock') || 0),
                },
              })
              .then(() => {
                notify('Variant added.', 'success');
              })
          }
        >
          {variantFields()}
        </FormDialog>
      }
    >
      <DataTable
        caption="Variants"
        rows={product.variants}
        rowKey={(v) => v.id}
        columns={[
          {
            header: 'Variant',
            cell: (v) => (
              <>
                {v.label} {v.is_default && <Badge tone="gold">default</Badge>}{' '}
                {!v.is_active && <Badge>inactive</Badge>}
                <span className="block text-xs text-ink-muted">{v.sku}</span>
              </>
            ),
          },
          { header: 'Net g', cell: (v) => v.net_gold_weight_g ?? '—', className: 'text-right' },
          {
            header: 'Stock',
            cell: (v) => `${String(v.on_hand)} (${String(v.reserved)} reserved)`,
            className: 'text-right',
          },
          {
            header: 'Customer price',
            cell: (v) =>
              v.unit_price ? (
                formatMoney(v.unit_price, { paise: hasPaise(v.unit_price) })
              ) : (
                <span className="text-danger">{v.price_error}</span>
              ),
            className: 'text-right tabular',
          },
          {
            header: '',
            cell: (v) => (
              <FormDialog
                title={`Edit ${v.sku}`}
                description="Stock is changed under Inventory, so every change is recorded."
                submitLabel="Save variant"
                trigger={(open) => (
                  <Button size="sm" variant="ghost" onClick={open}>
                    Edit
                  </Button>
                )}
                onSubmit={(form) =>
                  update
                    .mutateAsync({ id: product.id, variantId: v.id, body: fromForm(form) })
                    .then(() => {
                      notify('Variant saved.', 'success');
                    })
                }
              >
                {variantFields(v)}
              </FormDialog>
            ),
          },
        ]}
      />
    </Panel>
  );
}

function ImagesEditor({ product }: { product: AdminProduct }) {
  const upload = useUploadImage();
  const action = useImageAction();
  const { notify } = useToast();
  const [alt, setAlt] = useState('');
  const images = product.images;
  const move = (index: number, by: number) => {
    const ids = images.map((i) => i.id);
    const [moved] = ids.splice(index, 1);
    if (!moved) return;
    ids.splice(index + by, 0, moved);
    action.mutate({ kind: 'order', id: product.id, imageIds: ids });
  };
  return (
    <Panel title="Photos">
      <p className="mb-3 text-sm text-ink-muted">
        JPEG, PNG or WebP up to 10 MB, at least 400 px. Photos are converted to WebP in several
        sizes and camera/location data is removed. The first photo is the main one.
      </p>
      <div className="flex flex-wrap items-end gap-3">
        <FormField
          label="Description for screen readers"
          hint="What the photo shows"
          className="min-w-56 flex-1"
        >
          <Input
            value={alt}
            maxLength={200}
            onChange={(e) => {
              setAlt(e.target.value);
            }}
          />
        </FormField>
        <label className="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-sm border border-ink/80 px-4 text-sm hover:bg-ink hover:text-ivory has-focus-visible:outline-2 has-focus-visible:outline-focus">
          <ImagePlus className="size-4" aria-hidden="true" />
          {upload.isPending ? 'Uploading…' : 'Upload photo'}
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="sr-only"
            disabled={upload.isPending}
            onChange={(e) => {
              const file = e.target.files?.[0];
              e.target.value = '';
              if (!file) return;
              upload.mutate(
                { id: product.id, file, alt },
                {
                  onSuccess: () => {
                    setAlt('');
                    notify('Photo uploaded.', 'success');
                  },
                  onError: (err) => {
                    notify(errorMessage(err), 'error');
                  },
                },
              );
            }}
          />
        </label>
      </div>
      {images.length > 0 && (
        <ul className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {images.map((image, index) => (
            <li key={image.id} className="space-y-2">
              <div className="overflow-hidden rounded-sm bg-surface-muted">
                <ProductImage
                  image={{
                    url: image.url,
                    alt: image.alt_text,
                    width: image.width,
                    height: image.height,
                    renditions: image.renditions,
                    is_placeholder: image.is_placeholder,
                  }}
                  sizes="200px"
                  className="aspect-4/5 w-full object-cover"
                />
              </div>
              <p className="line-clamp-2 text-xs text-ink-muted">
                {image.is_placeholder ? 'Sample image · ' : ''}
                {image.alt_text}
              </p>
              <div className="flex flex-wrap gap-1">
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={index === 0}
                  aria-label={`Move photo ${String(index + 1)} earlier`}
                  onClick={() => {
                    move(index, -1);
                  }}
                >
                  <ArrowUp className="size-4" aria-hidden="true" />
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={index === images.length - 1}
                  aria-label={`Move photo ${String(index + 1)} later`}
                  onClick={() => {
                    move(index, 1);
                  }}
                >
                  <ArrowDown className="size-4" aria-hidden="true" />
                </Button>
                <FormDialog
                  title="Photo description"
                  submitLabel="Save"
                  trigger={(open) => (
                    <Button size="sm" variant="ghost" onClick={open}>
                      Describe
                    </Button>
                  )}
                  onSubmit={(form) =>
                    action.mutateAsync({
                      kind: 'alt',
                      id: product.id,
                      imageId: image.id,
                      alt: field(form, 'alt'),
                    })
                  }
                >
                  <FormField label="Description">
                    <Input name="alt" maxLength={200} defaultValue={image.alt_text} />
                  </FormField>
                </FormDialog>
                <FormDialog
                  title="Delete this photo?"
                  submitLabel="Delete photo"
                  danger
                  trigger={(open) => (
                    <Button
                      size="sm"
                      variant="ghost"
                      aria-label={`Delete photo ${String(index + 1)}`}
                      onClick={open}
                    >
                      <Trash2 className="size-4" aria-hidden="true" />
                    </Button>
                  )}
                  onSubmit={() =>
                    action.mutateAsync({ kind: 'delete', id: product.id, imageId: image.id })
                  }
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

function ProductEditor({
  product,
  categories,
  collections,
}: {
  product?: AdminProduct;
  categories: AdminCategory[];
  collections: AdminCollection[];
}) {
  const navigate = useNavigate();
  const create = useCreateProduct();
  const update = useUpdateProduct();
  const { notify } = useToast();
  const form = useForm<ProductForm>({ defaultValues: toForm(product) });
  const variants = useFieldArray({ control: form.control, name: 'variants' });
  const values = useWatch({ control: form.control }) as ProductForm;
  const mutation = product ? update : create;

  return (
    <form
      noValidate
      className="space-y-6"
      onSubmit={form.handleSubmit((f) => {
        if (product) {
          update.mutate(
            { id: product.id, body: productBody(f) },
            {
              onSuccess: () => {
                notify('Product saved.', 'success');
              },
            },
          );
        } else {
          const body: ProductCreateInput = {
            ...productBody(f),
            variants: f.variants.map((v) => ({
              ...variantBody(v),
              initial_stock: Number(v.initial_stock || 0),
            })),
          };
          create.mutate(body, {
            onSuccess: (created) => {
              notify('Product created as a draft. Add photos, then publish.', 'success');
              void navigate(`/admin/products/${created.id}`, { replace: true });
            },
          });
        }
      })}
    >
      <ServerErrors error={mutation.error} />
      {product && product.publish_problems.length > 0 && (
        <Alert tone="warning" title="Not ready to publish">
          <ul className="list-disc pl-5">
            {product.publish_problems.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        </Alert>
      )}
      <Panel title="Basics">
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="Name" required>
            <Input {...form.register('name', { required: true })} />
          </FormField>
          <FormField
            label="Web address"
            hint="Lowercase words and hyphens; created from the name if empty"
          >
            <Input {...form.register('slug')} />
          </FormField>
          <FormField label="Category" required>
            <Select {...form.register('category_id', { required: true })}>
              <option value="">Choose…</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.parent_id ? '— ' : ''}
                  {c.name}
                </option>
              ))}
            </Select>
          </FormField>
          <FormField label="Status" hint="Active = visible to customers">
            <Select {...form.register('status')}>
              <option value="draft">Draft</option>
              <option value="active">Active</option>
              <option value="archived">Archived</option>
            </Select>
          </FormField>
          <FormField label="Purity">
            <Select {...form.register('purity')}>
              {['24K', '22K', '18K', '14K'].map((p) => (
                <option key={p}>{p}</option>
              ))}
            </Select>
          </FormField>
          <FormField label="Metal colour">
            <Select {...form.register('metal_colour')}>
              <option value="yellow">Yellow gold</option>
              <option value="white">White gold</option>
              <option value="rose">Rose gold</option>
              <option value="two_tone">Two-tone</option>
            </Select>
          </FormField>
        </div>
      </Panel>
      <Panel title="Pricing inputs">
        <p className="mb-4 text-sm text-ink-muted">
          You enter the inputs; the store calculates what customers pay from the current gold rate,
          making charges and GST.
        </p>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <FormField label="Pricing">
            <Select {...form.register('pricing_model')}>
              <option value="weight_based">By weight × gold rate</option>
              <option value="fixed">Fixed price</option>
            </Select>
          </FormField>
          <FormField label="Making charge">
            <Select {...form.register('making_charge_type')}>
              <option value="percent">% of metal value</option>
              <option value="per_gram">₹ per gram</option>
              <option value="flat">Flat ₹</option>
              <option value="none">None</option>
            </Select>
          </FormField>
          <FormField label="Making charge value">
            <Input inputMode="decimal" {...form.register('making_charge_value')} />
          </FormField>
          <FormField label="Wastage %" hint="Optional">
            <Input inputMode="decimal" {...form.register('wastage_percent')} />
          </FormField>
        </div>
      </Panel>
      {!product && (
        <Panel
          title="Variants"
          actions={
            <Button
              type="button"
              size="sm"
              variant="secondary"
              onClick={() => {
                variants.append({ ...EMPTY_VARIANT });
              }}
            >
              <Plus className="size-4" aria-hidden="true" /> Add variant
            </Button>
          }
        >
          <div className="space-y-6">
            {variants.fields.map((item, index) => (
              <fieldset key={item.id} className="rounded-sm border border-line p-4">
                <legend className="px-1 text-sm font-medium">Variant {index + 1}</legend>
                <VariantFields register={form.register} prefix={`variants.${index}`} withStock />
                {variants.fields.length > 1 && (
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    className="mt-2"
                    onClick={() => {
                      variants.remove(index);
                    }}
                  >
                    Remove variant {index + 1}
                  </Button>
                )}
              </fieldset>
            ))}
          </div>
        </Panel>
      )}
      <PricePreviewPanel form={values} />
      <Panel title="Description and details">
        <div className="grid gap-4">
          <FormField label="Description">
            <Textarea rows={4} {...form.register('description')} />
          </FormField>
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label="Stone details">
              <Textarea rows={2} {...form.register('stone_details')} />
            </FormField>
            <FormField label="Hallmark details" hint="Only what is true for this piece">
              <Textarea rows={2} {...form.register('hallmark_details')} />
            </FormField>
            <FormField label="Certification details" hint="Only certificates you actually hold">
              <Textarea rows={2} {...form.register('certification_details')} />
            </FormField>
            <FormField label="Care instructions">
              <Textarea rows={2} {...form.register('care_instructions')} />
            </FormField>
          </div>
          <FormField label="Filters" hint="One per line, e.g. occasion: wedding">
            <Textarea rows={3} {...form.register('attributes')} />
          </FormField>
        </div>
      </Panel>
      <Panel title="Policies, highlights and collections">
        <div className="grid gap-3 sm:grid-cols-2">
          {(
            [
              ['return_eligible', 'Can be returned'],
              ['exchange_eligible', 'Can be exchanged'],
              ['is_featured', 'Featured on the home page'],
              ['is_bestseller', 'Mark as bestseller'],
            ] as const
          ).map(([name, label]) => (
            <label key={name} className="flex items-center gap-2 text-sm">
              <input type="checkbox" className="size-4 accent-ink" {...form.register(name)} />{' '}
              {label}
            </label>
          ))}
          <FormField label="Return window (days)">
            <Input inputMode="numeric" {...form.register('return_window_days')} />
          </FormField>
        </div>
        {collections.length > 0 && (
          <fieldset className="mt-4">
            <legend className="mb-2 text-sm font-medium">Collections</legend>
            <div className="flex flex-wrap gap-4">
              {collections.map((c) => (
                <label key={c.id} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    value={c.id}
                    className="size-4 accent-ink"
                    {...form.register('collection_ids')}
                  />{' '}
                  {c.name}
                </label>
              ))}
            </div>
          </fieldset>
        )}
      </Panel>
      <Panel title="Search engines">
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="SEO title">
            <Input maxLength={120} {...form.register('seo_title')} />
          </FormField>
          <FormField label="SEO description">
            <Textarea rows={2} maxLength={300} {...form.register('seo_description')} />
          </FormField>
        </div>
      </Panel>
      <div className="sticky bottom-0 -mx-4 flex flex-wrap items-center gap-3 border-t border-line bg-ivory/95 px-4 py-3 sm:-mx-8 sm:px-8">
        <Button type="submit" loading={mutation.isPending}>
          {product ? 'Save product' : 'Create draft'}
        </Button>
        {product?.status === 'active' && (
          <Link
            to={`/products/${product.slug}`}
            className="text-sm underline underline-offset-4"
            target="_blank"
            rel="noopener"
          >
            View in store
          </Link>
        )}
      </div>
    </form>
  );
}

export function AdminProductEditPage() {
  const { id } = useParams();
  const isNew = id === 'new' || id === undefined;
  const product = useAdminProduct(isNew ? undefined : id);
  // The form is created once, so its select lists must be loaded before it renders.
  const categories = useAdminCategories();
  const collections = useAdminCollections();
  if ((!isNew && product.isPending) || categories.isPending || collections.isPending) {
    return <Skeleton className="h-96" />;
  }
  if (categories.isError || collections.isError) {
    return (
      <ErrorState
        error={categories.error ?? collections.error}
        onRetry={() => {
          void categories.refetch();
          void collections.refetch();
        }}
      />
    );
  }
  if (!isNew && product.isError)
    return <ErrorState error={product.error} onRetry={() => void product.refetch()} />;
  const data = isNew ? undefined : product.data;
  return (
    <AdminPage
      title={data ? data.name : 'New product'}
      description={
        data
          ? `${data.status} · updated ${formatDateTime(data.updated_at)}${data.is_sample ? ' · sample product' : ''}`
          : 'Create a draft, add photos, then publish.'
      }
      actions={
        <Link to="/admin/products" className="text-sm underline underline-offset-4">
          All products
        </Link>
      }
    >
      <div className="space-y-6">
        {data && <VariantsEditor product={data} />}
        {data && <ImagesEditor product={data} />}
        <ProductEditor
          key={data?.id ?? 'new'}
          product={data}
          categories={categories.data}
          collections={collections.data}
        />
      </div>
    </AdminPage>
  );
}

// --------------------------------------------------------------------------- categories & collections

function CategoryDialog({ category, all }: { category?: AdminCategory; all: AdminCategory[] }) {
  const save = useSaveCategory();
  return (
    <FormDialog
      title={category ? `Edit ${category.name}` : 'New category'}
      submitLabel="Save category"
      trigger={(open) =>
        category ? (
          <Button size="sm" variant="ghost" onClick={open}>
            Edit
          </Button>
        ) : (
          <Button size="sm" variant="secondary" onClick={open}>
            <Plus className="size-4" aria-hidden="true" /> New category
          </Button>
        )
      }
      onSubmit={(form) =>
        save.mutateAsync({
          id: category?.id,
          body: {
            name: field(form, 'name'),
            slug: opt(field(form, 'slug')),
            parent_id: opt(field(form, 'parent_id')),
            description: opt(field(form, 'description')),
            sort_order: Number(field(form, 'sort_order') || 0),
            is_active: form.get('is_active') === 'on',
          },
        })
      }
    >
      <FormField label="Name" required>
        <Input name="name" required defaultValue={category?.name} />
      </FormField>
      <FormField label="Web address" hint="Created from the name if empty">
        <Input name="slug" defaultValue={category?.slug} />
      </FormField>
      <FormField label="Parent">
        <Select name="parent_id" defaultValue={category?.parent_id ?? ''}>
          <option value="">None (top level)</option>
          {all
            .filter((c) => !c.parent_id && c.id !== category?.id)
            .map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
        </Select>
      </FormField>
      <FormField label="Description">
        <Textarea name="description" rows={2} defaultValue={category?.description ?? ''} />
      </FormField>
      <FormField label="Order">
        <Input name="sort_order" inputMode="numeric" defaultValue={category?.sort_order ?? 0} />
      </FormField>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          name="is_active"
          defaultChecked={category?.is_active ?? true}
          className="size-4 accent-ink"
        />{' '}
        Visible in the store
      </label>
    </FormDialog>
  );
}

function CollectionDialog({ collection }: { collection?: AdminCollection }) {
  const save = useSaveCollection();
  const products = useAdminProducts({ page: 1, status: 'active' });
  return (
    <FormDialog
      title={collection ? `Edit ${collection.name}` : 'New collection'}
      submitLabel="Save collection"
      trigger={(open) =>
        collection ? (
          <Button size="sm" variant="ghost" onClick={open}>
            Edit
          </Button>
        ) : (
          <Button size="sm" variant="secondary" onClick={open}>
            <Plus className="size-4" aria-hidden="true" /> New collection
          </Button>
        )
      }
      onSubmit={(form) =>
        save.mutateAsync({
          id: collection?.id,
          body: {
            name: field(form, 'name'),
            slug: opt(field(form, 'slug')),
            description: opt(field(form, 'description')),
            is_active: form.get('is_active') === 'on',
            is_featured: form.get('is_featured') === 'on',
            sort_order: Number(field(form, 'sort_order') || 0),
            product_ids: form.getAll('product_ids').map(String),
          },
        })
      }
    >
      <FormField label="Name" required>
        <Input name="name" required defaultValue={collection?.name} />
      </FormField>
      <FormField label="Web address" hint="Created from the name if empty">
        <Input name="slug" defaultValue={collection?.slug} />
      </FormField>
      <FormField label="Description">
        <Textarea name="description" rows={2} defaultValue={collection?.description ?? ''} />
      </FormField>
      <FormField label="Order">
        <Input name="sort_order" inputMode="numeric" defaultValue={collection?.sort_order ?? 0} />
      </FormField>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          name="is_active"
          defaultChecked={collection?.is_active ?? true}
          className="size-4 accent-ink"
        />{' '}
        Visible in the store
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          name="is_featured"
          defaultChecked={collection?.is_featured ?? false}
          className="size-4 accent-ink"
        />{' '}
        Featured on the home page
      </label>
      <fieldset>
        <legend className="mb-2 text-sm font-medium">Products (first 25 active)</legend>
        <div className="max-h-48 space-y-1 overflow-y-auto">
          {products.data?.items.map((p) => (
            <label key={p.id} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                name="product_ids"
                value={p.id}
                defaultChecked={collection?.product_ids.includes(p.id)}
                className="size-4 accent-ink"
              />{' '}
              {p.name}
            </label>
          ))}
        </div>
      </fieldset>
    </FormDialog>
  );
}

export function AdminCategoriesPage() {
  const categories = useAdminCategories();
  const collections = useAdminCollections();
  const remove = useDeleteCategory();
  const { notify } = useToast();
  return (
    <AdminPage title="Categories & collections">
      <div className="space-y-6">
        <Panel
          title="Categories"
          actions={categories.data && <CategoryDialog all={categories.data} />}
        >
          <DataTable
            caption="Categories"
            rows={categories.data}
            rowKey={(c) => c.id}
            loading={categories.isPending}
            error={categories.error}
            columns={[
              { header: 'Name', cell: (c) => `${c.parent_id ? '— ' : ''}${c.name}` },
              { header: 'Address', cell: (c) => `/collections/${c.slug}` },
              { header: 'Products', cell: (c) => c.product_count, className: 'text-right' },
              { header: 'Visible', cell: (c) => (c.is_active ? 'Yes' : 'Hidden') },
              {
                header: '',
                cell: (c) => (
                  <div className="flex gap-1">
                    <CategoryDialog category={c} all={categories.data ?? []} />
                    <Button
                      size="sm"
                      variant="ghost"
                      aria-label={`Delete ${c.name}`}
                      disabled={c.product_count > 0}
                      onClick={() => {
                        remove.mutate(c.id, {
                          onError: (e) => {
                            notify(errorMessage(e), 'error');
                          },
                        });
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
        <Panel title="Collections" actions={<CollectionDialog />}>
          <DataTable
            caption="Collections"
            rows={collections.data}
            rowKey={(c) => c.id}
            loading={collections.isPending}
            error={collections.error}
            columns={[
              { header: 'Name', cell: (c) => c.name },
              { header: 'Products', cell: (c) => c.product_ids.length, className: 'text-right' },
              { header: 'Visible', cell: (c) => (c.is_active ? 'Yes' : 'Hidden') },
              { header: 'Featured', cell: (c) => (c.is_featured ? 'Yes' : '') },
              { header: '', cell: (c) => <CollectionDialog collection={c} /> },
            ]}
          />
        </Panel>
      </div>
    </AdminPage>
  );
}
