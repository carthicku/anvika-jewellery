/** Friendly names for generated API schema types (source: src/api/schema.d.ts). */
import type { components } from './schema';

type Schemas = components['schemas'];

export type ProductCard = Schemas['ProductCardOut'];
export type ProductDetail = Schemas['ProductDetailOut'];
export type Variant = Schemas['VariantOut'];
export type Price = Schemas['PriceOut'];
export type PriceRow = Schemas['PriceRowOut'];
export type Image = Schemas['ImageOut'];
export type Category = Schemas['CategoryOut'];
export type Collection = Schemas['CollectionOut'];
export type Facets = Schemas['FacetsOut'];
export type FacetValue = Schemas['FacetValueOut'];
export type Home = Schemas['HomeOut'];
export type Suggestions = Schemas['SuggestOut'];
export type Listing = Schemas['ListingOut'];
export type PublicSettings = Schemas['PublicSettingsOut'];
export type ContentPage = Schemas['ContentPageOut'];
export type PincodeCheck = Schemas['PincodeCheckOut'];
export type ProductPage = Schemas['Page_ProductCardOut_'];
export type StockStatus = ProductCard['stock_status'];
