"use server";

import { supabase } from "../lib/supabase";

export type BestPriceRow = {
  store_id: string;
  store_name: string;
  base_price: number;
  in_stock: boolean;
  product_url: string;
  bank_name: string | null;
  discount_percentage: number | null;
  max_refund_amount: number | null;
  final_price: number;
};

export type ProductWithBestPrice = {
  id: string;
  name: string;
  main_image_url: string | null;
  best: BestPriceRow | null;
};

async function attachBestPrices(
  products: { id: string; name: string; main_image_url: string | null }[]
): Promise<ProductWithBestPrice[]> {
  const withBest = await Promise.all(
    products.map(async (product) => {
      const { data: bestRows } = await supabase.rpc("best_price_today", {
        p_product_id: product.id,
      });
      const best = (bestRows as BestPriceRow[] | null)?.[0] ?? null;
      return { ...product, best };
    })
  );

  return withBest
    .filter((p) => p.best !== null)
    .sort((a, b) => (a.best!.final_price ?? 0) - (b.best!.final_price ?? 0));
}

export async function getLatestProducts(): Promise<ProductWithBestPrice[]> {
  const { data: products, error } = await supabase
    .from("products")
    .select("id, name, main_image_url")
    .limit(24);

  if (error || !products) {
    console.error(error);
    return [];
  }
  return attachBestPrices(products);
}

export async function searchProducts(query: string): Promise<ProductWithBestPrice[]> {
  const trimmed = query.trim();
  if (trimmed.length < 2) return [];

  const { data: products, error } = await supabase
    .from("products")
    .select("id, name, main_image_url")
    .ilike("name", `%${trimmed}%`)
    .limit(24);

  if (error || !products) {
    console.error(error);
    return [];
  }
  return attachBestPrices(products);
}
