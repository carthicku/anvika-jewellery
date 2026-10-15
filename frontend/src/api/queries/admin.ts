/**
 * Admin API hooks. Authorisation is enforced by the backend on every call (the admin UI only hides
 * links the user can't use). Mutations invalidate the affected admin queries.
 */
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
  type QueryKey,
} from '@tanstack/react-query';

import type { components } from '../schema';
import { api, unwrap } from '../client';

type S = components['schemas'];
export type AdminOrder = S['AdminOrderOut'];
export type AdminOrderRow = S['AdminOrderRowOut'];
export type Dashboard = S['DashboardOut'];
export type InventoryRow = S['InventoryRowOut'];
export type GoldRates = S['GoldRatesOut'];
export type RatePreview = S['RatePreviewOut'];
export type AdminProduct = S['AdminProductOut'];
export type ProductRow = S['ProductRowOut'];
export type ProductCreateInput = S['ProductCreateIn'];
export type ProductInput = S['ProductIn'];
export type VariantInput = S['VariantIn'];
export type VariantCreateInput = S['VariantCreateIn'];
export type AdminCategory = S['AdminCategoryOut'];
export type AdminCollection = S['AdminCollectionOut'];
export type Discount = S['DiscountOut'];
export type DiscountInput = S['DiscountIn'];
export type Coupon = S['CouponOut'];
export type CouponCreateInput = S['CouponCreateIn'];
export type ShippingMethod = S['ShippingMethodOut'];
export type ShippingZone = S['ShippingZoneOut'];
export type ContentPageAdmin = S['AdminContentPageOut'];
export type AdminSettings = S['SettingsOut'];
export type StaffUser = S['StaffUserOut'];

export const adminKeys = {
  all: ['admin'] as const,
  dashboard: ['admin', 'dashboard'] as const,
  orders: (params: object) => ['admin', 'orders', params] as const,
  order: (ref: string) => ['admin', 'order', ref] as const,
  inventory: (params: object) => ['admin', 'inventory', params] as const,
  movements: (params: object) => ['admin', 'movements', params] as const,
  goldRates: ['admin', 'gold-rates'] as const,
  products: (params: object) => ['admin', 'products', params] as const,
  product: (id: string) => ['admin', 'product', id] as const,
  categories: ['admin', 'categories'] as const,
  collections: ['admin', 'collections'] as const,
  customers: (params: object) => ['admin', 'customers', params] as const,
  customer: (id: string) => ['admin', 'customer', id] as const,
  discounts: ['admin', 'discounts'] as const,
  coupons: ['admin', 'coupons'] as const,
  shippingMethods: ['admin', 'shipping', 'methods'] as const,
  shippingZones: ['admin', 'shipping', 'zones'] as const,
  content: ['admin', 'content'] as const,
  contentPage: (slug: string) => ['admin', 'content', slug] as const,
  enquiries: (params: object) => ['admin', 'enquiries', params] as const,
  settings: ['admin', 'settings'] as const,
  users: ['admin', 'users'] as const,
  audit: (params: object) => ['admin', 'audit', params] as const,
};

/** A mutation that refreshes the given admin queries afterwards. */
function useAdminMutation<TVars, TResult>(
  fn: (vars: TVars) => Promise<TResult>,
  invalidate: QueryKey[] = [adminKeys.all],
) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: async () => {
      await Promise.all(invalidate.map((queryKey) => client.invalidateQueries({ queryKey })));
    },
  });
}

// --------------------------------------------------------------------------- dashboard & orders

export function useDashboard() {
  return useQuery({
    queryKey: adminKeys.dashboard,
    queryFn: () => unwrap(api.GET('/api/v1/admin/dashboard')),
  });
}

export interface OrderFilters {
  status?: string;
  payment_status?: string;
  q?: string;
  page: number;
}

export function useAdminOrders(filters: OrderFilters) {
  return useQuery({
    queryKey: adminKeys.orders(filters),
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/admin/orders', {
          params: {
            query: {
              status: filters.status || undefined,
              payment_status: filters.payment_status || undefined,
              q: filters.q || undefined,
              page: filters.page,
            },
          },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}

export function useAdminOrder(reference: string) {
  return useQuery({
    queryKey: adminKeys.order(reference),
    queryFn: () =>
      unwrap(api.GET('/api/v1/admin/orders/{reference}', { params: { path: { reference } } })),
  });
}

export function useOrderAction() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (
      action:
        | { kind: 'status'; reference: string; action: 'start_processing' | 'mark_delivered' }
        | {
            kind: 'ship';
            reference: string;
            carrier: string;
            tracking_number: string;
            tracking_url: string | null;
          }
        | { kind: 'cancel'; reference: string; reason: string }
        | { kind: 'note'; reference: string; note: string }
        | { kind: 'review'; reference: string; decision: 'confirm' | 'refund'; note: string }
        | { kind: 'refund'; reference: string; amount: string; reason: string }
        | { kind: 'execute_refund'; reference: string; refund_id: string },
    ) => {
      const path = { reference: action.reference };
      switch (action.kind) {
        case 'status':
          return unwrap(
            api.POST('/api/v1/admin/orders/{reference}/status', {
              params: { path },
              body: { action: action.action },
            }),
          );
        case 'ship':
          return unwrap(
            api.POST('/api/v1/admin/orders/{reference}/shipments', {
              params: { path },
              body: {
                carrier: action.carrier,
                tracking_number: action.tracking_number,
                tracking_url: action.tracking_url,
              },
            }),
          );
        case 'cancel':
          return unwrap(
            api.POST('/api/v1/admin/orders/{reference}/cancel', {
              params: { path },
              body: { reason: action.reason },
            }),
          );
        case 'note':
          return unwrap(
            api.POST('/api/v1/admin/orders/{reference}/notes', {
              params: { path },
              body: { note: action.note },
            }),
          );
        case 'review':
          return unwrap(
            api.POST('/api/v1/admin/orders/{reference}/review', {
              params: { path },
              body: { decision: action.decision, note: action.note },
            }),
          );
        case 'refund':
          return unwrap(
            api.POST('/api/v1/admin/orders/{reference}/refunds', {
              params: { path },
              body: { amount: action.amount, reason: action.reason },
            }),
          );
        case 'execute_refund':
          return unwrap(
            api.POST('/api/v1/admin/orders/{reference}/refunds/{refund_id}/execute', {
              params: { path: { reference: action.reference, refund_id: action.refund_id } },
            }),
          );
      }
    },
    onSuccess: (order) => {
      client.setQueryData(adminKeys.order(order.order.reference), order);
      void client.invalidateQueries({ queryKey: ['admin', 'orders'] });
      void client.invalidateQueries({ queryKey: adminKeys.dashboard });
    },
  });
}

// --------------------------------------------------------------------------- inventory

export function useInventory(params: { q?: string; low_only?: boolean; page: number }) {
  return useQuery({
    queryKey: adminKeys.inventory(params),
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/admin/inventory', {
          params: {
            query: { q: params.q || undefined, low_only: params.low_only, page: params.page },
          },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}

export function useMovements(params: { variant_id?: string; page: number }) {
  return useQuery({
    queryKey: adminKeys.movements(params),
    queryFn: () =>
      unwrap(api.GET('/api/v1/admin/inventory/movements', { params: { query: params } })),
    placeholderData: keepPreviousData,
  });
}

export function useAdjustStock() {
  return useAdminMutation(
    ({ variantId, delta, note }: { variantId: string; delta: number; note: string }) =>
      unwrap(
        api.POST('/api/v1/admin/inventory/{variant_id}/adjust', {
          params: { path: { variant_id: variantId } },
          body: { delta, note },
        }),
      ),
  );
}

export function useSetThreshold() {
  return useAdminMutation(({ variantId, value }: { variantId: string; value: number }) =>
    unwrap(
      api.PUT('/api/v1/admin/inventory/{variant_id}/threshold', {
        params: { path: { variant_id: variantId } },
        body: { low_stock_threshold: value },
      }),
    ),
  );
}

// --------------------------------------------------------------------------- gold rates

export function useGoldRates() {
  return useQuery({
    queryKey: adminKeys.goldRates,
    queryFn: () => unwrap(api.GET('/api/v1/admin/gold-rates')),
  });
}

export function usePreviewRate() {
  return useMutation({
    mutationFn: (body: S['RatePreviewIn']) =>
      unwrap(api.POST('/api/v1/admin/gold-rates/preview', { body })),
  });
}

export function useCreateRate() {
  return useAdminMutation((body: S['CreateRateIn']) =>
    unwrap(api.POST('/api/v1/admin/gold-rates', { body })),
  );
}

// --------------------------------------------------------------------------- catalogue

export function useAdminProducts(params: { q?: string; status?: string; page: number }) {
  return useQuery({
    queryKey: adminKeys.products(params),
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/admin/products', {
          params: {
            query: {
              q: params.q || undefined,
              status: params.status || undefined,
              page: params.page,
            },
          },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}

export function useAdminProduct(id: string | undefined) {
  return useQuery({
    queryKey: adminKeys.product(id ?? 'new'),
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/admin/products/{product_id}', {
          params: { path: { product_id: id ?? '' } },
        }),
      ),
    enabled: Boolean(id),
  });
}

function useProductMutation<TVars>(fn: (vars: TVars) => Promise<AdminProduct>) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: (product) => {
      client.setQueryData(adminKeys.product(product.id), product);
      void client.invalidateQueries({ queryKey: ['admin', 'products'] });
    },
  });
}

export function useCreateProduct() {
  return useProductMutation((body: ProductCreateInput) =>
    unwrap(api.POST('/api/v1/admin/products', { body })),
  );
}

export function useUpdateProduct() {
  return useProductMutation(({ id, body }: { id: string; body: ProductInput }) =>
    unwrap(
      api.PUT('/api/v1/admin/products/{product_id}', {
        params: { path: { product_id: id } },
        body,
      }),
    ),
  );
}

export function useAddVariant() {
  return useProductMutation(({ id, body }: { id: string; body: VariantCreateInput }) =>
    unwrap(
      api.POST('/api/v1/admin/products/{product_id}/variants', {
        params: { path: { product_id: id } },
        body,
      }),
    ),
  );
}

export function useUpdateVariant() {
  return useProductMutation(
    ({ id, variantId, body }: { id: string; variantId: string; body: VariantInput }) =>
      unwrap(
        api.PUT('/api/v1/admin/products/{product_id}/variants/{variant_id}', {
          params: { path: { product_id: id, variant_id: variantId } },
          body,
        }),
      ),
  );
}

export function useUploadImage() {
  return useProductMutation(({ id, file, alt }: { id: string; file: File; alt: string }) => {
    const form = new FormData();
    form.append('file', file);
    form.append('alt_text', alt);
    return unwrap(
      api.POST('/api/v1/admin/products/{product_id}/images', {
        params: { path: { product_id: id } },
        // openapi-fetch sends FormData as multipart when the body is FormData.
        body: form as unknown as { file: string; alt_text: string },
        bodySerializer: (body: unknown) => body as FormData,
      }),
    );
  });
}

export function useImageAction() {
  return useProductMutation(
    (
      vars:
        | { kind: 'alt'; id: string; imageId: string; alt: string }
        | { kind: 'order'; id: string; imageIds: string[] }
        | { kind: 'delete'; id: string; imageId: string },
    ) => {
      if (vars.kind === 'alt')
        return unwrap(
          api.PATCH('/api/v1/admin/products/{product_id}/images/{image_id}', {
            params: { path: { product_id: vars.id, image_id: vars.imageId } },
            body: { alt_text: vars.alt },
          }),
        );
      if (vars.kind === 'order')
        return unwrap(
          api.PUT('/api/v1/admin/products/{product_id}/images/order', {
            params: { path: { product_id: vars.id } },
            body: { image_ids: vars.imageIds },
          }),
        );
      return unwrap(
        api.DELETE('/api/v1/admin/products/{product_id}/images/{image_id}', {
          params: { path: { product_id: vars.id, image_id: vars.imageId } },
        }),
      );
    },
  );
}

export function usePricePreview() {
  return useMutation({
    mutationFn: (body: S['PricePreviewIn']) =>
      unwrap(api.POST('/api/v1/admin/catalogue/price-preview', { body })),
  });
}

export function useAdminCategories() {
  return useQuery({
    queryKey: adminKeys.categories,
    queryFn: () => unwrap(api.GET('/api/v1/admin/categories')),
  });
}

export function useSaveCategory() {
  return useAdminMutation(({ id, body }: { id?: string; body: S['CategoryIn'] }) =>
    id
      ? unwrap(
          api.PUT('/api/v1/admin/categories/{category_id}', {
            params: { path: { category_id: id } },
            body,
          }),
        )
      : unwrap(api.POST('/api/v1/admin/categories', { body })),
  );
}

export function useDeleteCategory() {
  return useAdminMutation((id: string) =>
    unwrap(
      api.DELETE('/api/v1/admin/categories/{category_id}', {
        params: { path: { category_id: id } },
      }),
    ),
  );
}

export function useAdminCollections() {
  return useQuery({
    queryKey: adminKeys.collections,
    queryFn: () => unwrap(api.GET('/api/v1/admin/collections')),
  });
}

export function useSaveCollection() {
  return useAdminMutation(({ id, body }: { id?: string; body: S['CollectionIn'] }) =>
    id
      ? unwrap(
          api.PUT('/api/v1/admin/collections/{collection_id}', {
            params: { path: { collection_id: id } },
            body,
          }),
        )
      : unwrap(api.POST('/api/v1/admin/collections', { body })),
  );
}

// --------------------------------------------------------------------------- customers, enquiries

export function useCustomers(params: { q?: string; page: number }) {
  return useQuery({
    queryKey: adminKeys.customers(params),
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/admin/customers', {
          params: { query: { q: params.q || undefined, page: params.page } },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}

export function useCustomer(id: string) {
  return useQuery({
    queryKey: adminKeys.customer(id),
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/admin/customers/{customer_id}', { params: { path: { customer_id: id } } }),
      ),
  });
}

export function useEnquiries(params: { status?: string; page: number }) {
  return useQuery({
    queryKey: adminKeys.enquiries(params),
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/admin/enquiries', {
          params: { query: { status: params.status || undefined, page: params.page } },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}

export function useSetEnquiryStatus() {
  return useAdminMutation(
    ({ id, status }: { id: string; status: 'new' | 'in_progress' | 'closed' }) =>
      unwrap(
        api.PUT('/api/v1/admin/enquiries/{enquiry_id}/status', {
          params: { path: { enquiry_id: id } },
          body: { status },
        }),
      ),
  );
}

// --------------------------------------------------------------------------- promotions

export function useDiscounts() {
  return useQuery({
    queryKey: adminKeys.discounts,
    queryFn: () => unwrap(api.GET('/api/v1/admin/discounts')),
  });
}

export function useSaveDiscount() {
  return useAdminMutation(({ id, body }: { id?: string; body: DiscountInput }) =>
    id
      ? unwrap(
          api.PUT('/api/v1/admin/discounts/{discount_id}', {
            params: { path: { discount_id: id } },
            body,
          }),
        )
      : unwrap(api.POST('/api/v1/admin/discounts', { body })),
  );
}

export function useCoupons() {
  return useQuery({
    queryKey: adminKeys.coupons,
    queryFn: () => unwrap(api.GET('/api/v1/admin/coupons')),
  });
}

export function useSaveCoupon() {
  return useAdminMutation(
    ({ id, body }: { id?: string; body: CouponCreateInput | S['CouponUpdateIn'] }) =>
      id
        ? unwrap(
            api.PUT('/api/v1/admin/coupons/{coupon_id}', {
              params: { path: { coupon_id: id } },
              body: body,
            }),
          )
        : unwrap(api.POST('/api/v1/admin/coupons', { body: body as CouponCreateInput })),
  );
}

// --------------------------------------------------------------------------- shipping

export function useShippingMethods() {
  return useQuery({
    queryKey: adminKeys.shippingMethods,
    queryFn: () => unwrap(api.GET('/api/v1/admin/shipping/methods')),
  });
}

export function useSaveShippingMethod() {
  return useAdminMutation(({ id, body }: { id?: string; body: S['ShippingMethodIn'] }) =>
    id
      ? unwrap(
          api.PUT('/api/v1/admin/shipping/methods/{method_id}', {
            params: { path: { method_id: id } },
            body,
          }),
        )
      : unwrap(api.POST('/api/v1/admin/shipping/methods', { body })),
  );
}

export function useShippingZones() {
  return useQuery({
    queryKey: adminKeys.shippingZones,
    queryFn: () => unwrap(api.GET('/api/v1/admin/shipping/zones')),
  });
}

export function useSaveShippingZone() {
  return useAdminMutation(({ id, body }: { id?: string; body: S['ShippingZoneIn'] }) =>
    id
      ? unwrap(
          api.PUT('/api/v1/admin/shipping/zones/{zone_id}', {
            params: { path: { zone_id: id } },
            body,
          }),
        )
      : unwrap(api.POST('/api/v1/admin/shipping/zones', { body })),
  );
}

export function useDeleteShippingZone() {
  return useAdminMutation((id: string) =>
    unwrap(
      api.DELETE('/api/v1/admin/shipping/zones/{zone_id}', { params: { path: { zone_id: id } } }),
    ),
  );
}

// --------------------------------------------------------------------------- content & settings

export function useContentPages() {
  return useQuery({
    queryKey: adminKeys.content,
    queryFn: () => unwrap(api.GET('/api/v1/admin/content')),
  });
}

export function useSaveContentPage() {
  return useAdminMutation(({ slug, body }: { slug: string; body: S['ContentPageIn'] }) =>
    unwrap(api.PUT('/api/v1/admin/content/{slug}', { params: { path: { slug } }, body })),
  );
}

export function useAdminSettings() {
  return useQuery({
    queryKey: adminKeys.settings,
    queryFn: () => unwrap(api.GET('/api/v1/admin/settings')),
  });
}

export function useSaveSettings() {
  return useAdminMutation(
    (
      vars:
        | { group: 'store'; body: S['StoreSettingsIn'] }
        | { group: 'announcement'; body: S['AnnouncementIn'] }
        | { group: 'tax'; body: S['TaxIn-Input'] }
        | { group: 'pricing-policy'; body: S['PricingPolicyIn-Input'] },
    ) => {
      switch (vars.group) {
        case 'store':
          return unwrap(api.PUT('/api/v1/admin/settings/store', { body: vars.body }));
        case 'announcement':
          return unwrap(api.PUT('/api/v1/admin/settings/announcement', { body: vars.body }));
        case 'tax':
          return unwrap(api.PUT('/api/v1/admin/settings/tax', { body: vars.body }));
        case 'pricing-policy':
          return unwrap(api.PUT('/api/v1/admin/settings/pricing-policy', { body: vars.body }));
      }
    },
    [adminKeys.settings, ['settings', 'public']],
  );
}

// --------------------------------------------------------------------------- staff & audit

export function useStaffUsers() {
  return useQuery({
    queryKey: adminKeys.users,
    queryFn: () => unwrap(api.GET('/api/v1/admin/users')),
  });
}

export function useStaffAction() {
  return useAdminMutation(
    (
      vars:
        | { kind: 'promote'; email: string; role: 'staff' | 'admin' }
        | { kind: 'role'; id: string; role: 'customer' | 'staff' | 'admin' }
        | { kind: 'active'; id: string; is_active: boolean },
    ) => {
      if (vars.kind === 'promote')
        return unwrap(
          api.POST('/api/v1/admin/users/promote', { body: { email: vars.email, role: vars.role } }),
        );
      if (vars.kind === 'role')
        return unwrap(
          api.PUT('/api/v1/admin/users/{user_id}/role', {
            params: { path: { user_id: vars.id } },
            body: { role: vars.role },
          }),
        );
      return unwrap(
        api.PUT('/api/v1/admin/users/{user_id}/active', {
          params: { path: { user_id: vars.id } },
          body: { is_active: vars.is_active },
        }),
      );
    },
    [adminKeys.users],
  );
}

export function useAuditLogs(params: { entity_type?: string; action?: string; page: number }) {
  return useQuery({
    queryKey: adminKeys.audit(params),
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/admin/audit-logs', {
          params: {
            query: {
              entity_type: params.entity_type || undefined,
              action: params.action || undefined,
              page: params.page,
            },
          },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}

// --------------------------------------------------------------------------- returns & reviews

export type AdminReturn = S['AdminReturnOut'];
export type AdminReturnRow = S['AdminReturnRowOut'];
export type AdminReview = S['AdminReviewOut'];

export function useAdminReturns(params: { status?: string; page: number }) {
  return useQuery({
    queryKey: ['admin', 'returns', params],
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/admin/returns', {
          params: {
            query: {
              status: (params.status || undefined) as AdminReturnRow['status'] | undefined,
              page: params.page,
            },
          },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}

export function useAdminReturn(id: string) {
  return useQuery({
    queryKey: ['admin', 'return', id],
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/admin/returns/{request_id}', { params: { path: { request_id: id } } }),
      ),
  });
}

export type ReturnAction =
  | { action: 'approve' | 'reject' | 'close'; note: string }
  | { action: 'receive'; restock_positions: number[]; note: string }
  | { action: 'refund'; amount: string; note: string };

export function useReturnAction(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (vars: ReturnAction) => {
      const params = { path: { request_id: id } };
      switch (vars.action) {
        case 'approve':
          return unwrap(
            api.POST('/api/v1/admin/returns/{request_id}/approve', {
              params,
              body: { note: vars.note },
            }),
          );
        case 'reject':
          return unwrap(
            api.POST('/api/v1/admin/returns/{request_id}/reject', {
              params,
              body: { note: vars.note },
            }),
          );
        case 'close':
          return unwrap(
            api.POST('/api/v1/admin/returns/{request_id}/close', {
              params,
              body: { note: vars.note },
            }),
          );
        case 'receive':
          return unwrap(
            api.POST('/api/v1/admin/returns/{request_id}/receive', {
              params,
              body: { restock_positions: vars.restock_positions, note: vars.note },
            }),
          );
        case 'refund':
          return unwrap(
            api.POST('/api/v1/admin/returns/{request_id}/refund', {
              params,
              body: { amount: vars.amount, note: vars.note },
            }),
          );
      }
    },
    onSuccess: (data) => {
      client.setQueryData(['admin', 'return', id], data);
      void client.invalidateQueries({ queryKey: ['admin', 'returns'] });
      void client.invalidateQueries({ queryKey: adminKeys.order(data.order_reference) });
      void client.invalidateQueries({ queryKey: adminKeys.dashboard });
    },
  });
}

export function useAdminReviews(params: { status?: string; page: number }) {
  return useQuery({
    queryKey: ['admin', 'reviews', params],
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/admin/reviews', {
          params: {
            query: {
              status: (params.status || undefined) as AdminReview['status'] | undefined,
              page: params.page,
            },
          },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}

export function useModerateReview() {
  return useAdminMutation(
    ({ id, decision, note }: { id: string; decision: 'approve' | 'reject'; note: string }) =>
      unwrap(
        api.POST('/api/v1/admin/reviews/{review_id}/moderate', {
          params: { path: { review_id: id } },
          body: { decision, note },
        }),
      ),
    [['admin', 'reviews'], adminKeys.dashboard],
  );
}
