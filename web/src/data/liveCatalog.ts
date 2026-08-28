import { SHOP_ITEMS, PETS_DATA, BOSSES, CRAFT_RECIPES } from './gameData';

type ShopRec = (typeof SHOP_ITEMS)[string];
type PetRec = (typeof PETS_DATA)[string];
type BossRec = (typeof BOSSES)[string];

let shop: Record<string, ShopRec> = { ...SHOP_ITEMS };
let pets: Record<string, PetRec> = { ...PETS_DATA };
let bosses: Record<string, BossRec> = { ...BOSSES };
let recipes: typeof CRAFT_RECIPES = [...CRAFT_RECIPES];

export function applyBootstrapCatalogs(data: {
  shop?: any[];
  petCatalog?: any[];
  bossCatalog?: any[];
  recipes?: any[];
}) {
  if (Array.isArray(data.shop) && data.shop.length) {
    const next: Record<string, ShopRec> = {};
    for (const item of data.shop) {
      const id = String(item.id || item.itemId || '');
      if (!id) continue;
      next[id] = {
        ...(SHOP_ITEMS[id] || {}),
        ...item,
        id,
        name: item.name || id,
        icon: item.icon || '📦',
        type: item.type || 'consumable',
        price: Number(item.price || 0),
        sellPrice: Number(item.sellPrice || item.sell_price || 0),
        desc: item.desc || item.description || '',
        buffDesc: item.buffDesc || '',
        craftOnly: Boolean(item.craftOnly),
        buff: item.buff || {},
      } as ShopRec;
    }
    shop = next;
  }
  if (Array.isArray(data.petCatalog) && data.petCatalog.length) {
    const next: Record<string, PetRec> = {};
    for (const pet of data.petCatalog) {
      const id = String(pet.id || pet.petId || '');
      if (!id) continue;
      next[id] = {
        ...(PETS_DATA[id] || {}),
        ...pet,
        id,
        name: pet.name || id,
        icon: pet.icon || '🐾',
        price: Number(pet.price || 0),
        desc: pet.desc || pet.description || '',
        baseBuff: pet.baseBuff || pet.base_buff || {},
      } as PetRec;
    }
    pets = next;
  }
  if (Array.isArray(data.bossCatalog) && data.bossCatalog.length) {
    const next: Record<string, BossRec> = {};
    for (const b of data.bossCatalog) {
      const id = String(b.id || '');
      if (!id) continue;
      next[id] = {
        ...(BOSSES[id] || {}),
        ...b,
        id,
        name: b.name || id,
        icon: b.icon || '🐉',
        hp: Number(b.hp || b.maxHp || 0),
        atk: Number(b.atk || 0),
        xpReward: Number(b.xpReward || b.xp || 0),
        goldReward: Number(b.goldReward || b.gold || 0),
        minLevel: Number(b.minLevel || 1),
        tier: b.tier || 'normal',
      } as BossRec;
    }
    bosses = next;
  }
  if (Array.isArray(data.recipes) && data.recipes.length) {
    recipes = data.recipes.map((r: any) => ({
      id: String(r.id || r.resultItemId),
      resultItemId: String(r.resultItemId || r.id),
      goldCost: Number(r.goldCost || r.gold || 0),
      requiredItems: (r.requiredItems || []).map((x: any) =>
        typeof x === 'string'
          ? { itemId: x, quantity: 1 }
          : { itemId: x.itemId || x, quantity: Number(x.quantity || 1) }
      ),
    })) as typeof CRAFT_RECIPES;
  }
}

export function liveShopItems() {
  return shop;
}
export function livePets() {
  return pets;
}
export function liveBosses() {
  return bosses;
}
export function liveRecipes() {
  return recipes;
}
