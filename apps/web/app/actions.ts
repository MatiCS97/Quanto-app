"use server";

import { supabase } from "../lib/supabase";

export type BestPriceRow = {
  store_id: string;
  store_name: string;
  base_price: number;
  in_stock: boolean;
  product_url: string;
  bank_name: string | null;
  card_type: string | null;
  discount_percentage: number | null;
  max_refund_amount: number | null;
  final_price: number;
  is_indirect_source: boolean | null;
  source_note: string | null;
};

export type ProductWithBestPrice = {
  id: string;
  name: string;
  main_image_url: string | null;
  best: BestPriceRow | null;
};

export type ProductFilters = {
  category?: string;
  bankName?: string;
  cardType?: "credito" | "debito";
};

export type BankOption = {
  bankName: string;
  cardType: "credito" | "debito" | "ambas";
};

const RESULT_LIMIT = 24;
// Traemos más candidatos que RESULT_LIMIT porque el filtro por banco se
// aplica después de calcular best_price_today (RPC por producto) — no es
// una condición SQL directa sobre products. Con el catálogo actual (unos
// pocos cientos de filas) es aceptable; si crece mucho hay que mover el
// filtro de banco a una función SQL agregada.
const CANDIDATE_LIMIT = 200;

async function attachBestPrices(
  products: { id: string; name: string; main_image_url: string | null }[],
  filters?: ProductFilters
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

  let filtered = withBest.filter((p) => p.best !== null);

  if (filters?.bankName) {
    filtered = filtered.filter((p) => p.best!.bank_name === filters.bankName);
  }
  if (filters?.cardType) {
    // "ambas" en la promo significa que aplica tanto a crédito como a
    // débito — no es un tercer valor excluyente, así que matchea con
    // cualquiera de los dos filtros de tarjeta específicos.
    filtered = filtered.filter(
      (p) => p.best!.card_type === filters.cardType || p.best!.card_type === "ambas"
    );
  }

  return filtered
    .sort((a, b) => (a.best!.final_price ?? 0) - (b.best!.final_price ?? 0))
    .slice(0, RESULT_LIMIT);
}

export async function getCategories(): Promise<string[]> {
  const { data, error } = await supabase.from("products").select("category");
  if (error || !data) return [];
  return Array.from(new Set(data.map((d) => d.category))).sort();
}

export async function getActiveBanks(): Promise<BankOption[]> {
  const { data, error } = await supabase
    .from("bank_promotions")
    .select("bank_name, card_type")
    .eq("active", true);
  if (error || !data) return [];

  const seen = new Set<string>();
  const options: BankOption[] = [];
  for (const row of data) {
    const key = `${row.bank_name}::${row.card_type}`;
    if (seen.has(key)) continue;
    seen.add(key);
    options.push({ bankName: row.bank_name, cardType: row.card_type });
  }
  return options.sort((a, b) => a.bankName.localeCompare(b.bankName));
}

export async function getLatestProducts(filters?: ProductFilters): Promise<ProductWithBestPrice[]> {
  let builder = supabase.from("products").select("id, name, main_image_url");
  if (filters?.category) {
    builder = builder.eq("category", filters.category);
  }

  const { data: products, error } = await builder.limit(CANDIDATE_LIMIT);

  if (error || !products) {
    console.error(error);
    return [];
  }
  return attachBestPrices(products, filters);
}

export async function searchProducts(
  query: string,
  filters?: ProductFilters
): Promise<ProductWithBestPrice[]> {
  const trimmed = query.trim();
  if (trimmed.length < 2) return [];

  // Cada palabra se busca con un .ilike() propio; postgrest-js hace
  // .append() en el query string, así que dos condiciones sobre "name"
  // se combinan con AND (dos params name=ilike.X&name=ilike.Y), no se
  // sobrescriben.
  const words = trimmed.split(/\s+/).filter((w) => w.length > 0);

  if (words.length === 0) return [];

  let builder = supabase.from("products").select("id, name, main_image_url");
  for (const word of words) {
    builder = builder.ilike("name", `%${word}%`);
  }
  if (filters?.category) {
    builder = builder.eq("category", filters.category);
  }

  const { data: products, error } = await builder.limit(CANDIDATE_LIMIT);

  if (error || !products) {
    console.error(error);
    return [];
  }
  return attachBestPrices(products, filters);
}
