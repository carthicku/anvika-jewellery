/** Typed API fixtures for component tests (shapes come from the generated OpenAPI types). */
import type {
  Facets,
  Home,
  Price,
  ProductCard,
  ProductDetail,
  ProductPage,
  PublicSettings,
} from '@/api/types';

export const availablePrice = (amount: string, extra: Partial<Price> = {}): Price => ({
  available: true,
  currency: 'INR',
  amount,
  compare_at: null,
  discount_label: null,
  breakdown: [],
  gold_rate: null,
  unavailable_reason: null,
  ...extra,
});

export function card(overrides: Partial<ProductCard> = {}): ProductCard {
  return {
    id: 'p1',
    slug: 'everyday-gold-band',
    name: 'Everyday Gold Band',
    category: { slug: 'rings', name: 'Rings' },
    purity: '22K',
    metal_colour: 'yellow',
    weight_g: '3.480',
    image: {
      url: '/img/a.svg',
      alt: 'Band',
      width: 800,
      height: 1000,
      renditions: {},
      is_placeholder: true,
    },
    hover_image: null,
    price: availablePrice('27402.74'),
    price_is_from: false,
    stock_status: 'in_stock',
    is_sample: true,
    is_new: false,
    ...overrides,
  };
}

export const settings: PublicSettings = {
  store_name: 'Anvika',
  tagline: 'Fine gold jewellery',
  support_email: '[Support email — to be configured]',
  support_phone: '[Support phone — to be configured]',
  whatsapp: null,
  business_address: '[Business address — to be configured]',
  business_hours: '[Business hours — to be configured]',
  announcement: {
    enabled: true,
    text: 'Free standard delivery on orders above ₹25,000',
    link: null,
  },
  payment_mode: 'simulator',
  email_verification_required: false,
};

export const home: Home = {
  categories: [
    {
      slug: 'rings',
      name: 'Rings',
      description: null,
      image_url: null,
      parent_slug: null,
      seo_title: null,
      seo_description: null,
    },
  ],
  collections: [],
  new_arrivals: [card()],
  featured: [],
  bestsellers: [],
};

export function page(items: ProductCard[]): ProductPage {
  return { items, page: 1, page_size: 24, total: items.length, pages: 1 };
}

export const facets: Facets = {
  total: 2,
  categories: [{ value: 'rings', label: 'Rings', count: 2 }],
  purities: [
    { value: '22K', label: '22K', count: 1 },
    { value: '18K', label: '18K', count: 1 },
  ],
  metal_colours: [{ value: 'yellow', label: 'Yellow gold', count: 2 }],
  attributes: { occasion: [{ value: 'wedding', label: 'Wedding', count: 1 }] },
  price_min: '11510.25',
  price_max: '51256.92',
  in_stock_count: 2,
};

export const detail: ProductDetail = {
  id: 'p1',
  slug: 'everyday-gold-band',
  name: 'Everyday Gold Band',
  description: 'A smooth band.',
  category: { slug: 'rings', name: 'Rings' },
  parent_category: null,
  collections: [],
  purity: '22K',
  metal_colour: 'yellow',
  pricing_model: 'weight_based',
  stone_details: null,
  hallmark_details: null,
  certification_details: null,
  care_instructions: 'Keep dry.',
  return_eligible: true,
  exchange_eligible: false,
  return_window_days: 15,
  images: [
    {
      url: '/img/a.svg',
      alt: 'Band',
      width: 800,
      height: 1000,
      renditions: {},
      is_placeholder: true,
    },
  ],
  attributes: [],
  is_sample: true,
  seo_title: null,
  seo_description: null,
  published_at: '2026-10-01T00:00:00Z',
  variants: [
    {
      id: 'v10',
      sku: 'ANV-RG-002-10',
      label: 'Size 10',
      size: '10',
      gross_weight_g: '3.400',
      net_gold_weight_g: '3.400',
      stone_weight_ct: null,
      is_default: false,
      stock_status: 'out_of_stock',
      available_quantity: 0,
      price: availablePrice('26772.79'),
    },
    {
      id: 'v12',
      sku: 'ANV-RG-002-12',
      label: 'Size 12',
      size: '12',
      gross_weight_g: '3.480',
      net_gold_weight_g: '3.480',
      stone_weight_ct: null,
      is_default: true,
      stock_status: 'in_stock',
      available_quantity: 8,
      price: availablePrice('27402.74', {
        breakdown: [
          { key: 'metal', label: 'Gold value (22K)', amount: '24882.00' },
          { key: 'making', label: 'Making charges', amount: '1914.00' },
          { key: 'discount', label: '10% off making', amount: '-191.40' },
          { key: 'tax', label: 'GST', amount: '798.14' },
          { key: 'total', label: 'Total', amount: '27402.74' },
        ],
        gold_rate: {
          purity: '22K',
          rate_per_gram: '7150.00',
          effective_from: '2026-10-14T10:00:00Z',
        },
      }),
    },
  ],
};
