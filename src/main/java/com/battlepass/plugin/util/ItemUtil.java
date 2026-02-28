package com.battlepass.plugin.util;

import org.bukkit.Material;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.enchantments.Enchantment;
import org.bukkit.inventory.ItemFlag;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public final class ItemUtil {

    private ItemUtil() {
    }

    public static ItemStack createItem(ConfigurationSection section, ItemStack fallback, Map<String, String> placeholders) {
        if (section == null) {
            return fallback == null ? new ItemStack(Material.BARRIER) : fallback.clone();
        }

        String materialName = section.getString("material", "PAPER");
        Material material = Material.matchMaterial(materialName == null ? "PAPER" : materialName.toUpperCase());
        if (material == null) {
            material = Material.PAPER;
        }

        int amount = Math.max(1, Math.min(64, section.getInt("amount", 1)));
        ItemStack item = new ItemStack(material, amount);
        ItemMeta meta = item.getItemMeta();
        if (meta == null) {
            return item;
        }

        String name = section.getString("name");
        if (name != null) {
            meta.setDisplayName(ColorUtil.colorize(PlaceholderUtil.apply(name, placeholders)));
        }

        List<String> lore = section.getStringList("lore");
        if (!lore.isEmpty()) {
            List<String> coloredLore = new ArrayList<>();
            for (String line : lore) {
                coloredLore.add(ColorUtil.colorize(PlaceholderUtil.apply(line, placeholders)));
            }
            meta.setLore(coloredLore);
        }

        int cmd = section.getInt("custom-model-data", -1);
        if (cmd >= 0) {
            meta.setCustomModelData(cmd);
        }

        boolean enchanted = section.getBoolean("glint", false);
        if (enchanted) {
            meta.addEnchant(Enchantment.UNBREAKING, 1, true);
            meta.addItemFlags(ItemFlag.HIDE_ENCHANTS);
        }

        List<String> flags = section.getStringList("flags");
        for (String rawFlag : flags) {
            try {
                meta.addItemFlags(ItemFlag.valueOf(rawFlag.toUpperCase()));
            } catch (IllegalArgumentException ignored) {
            }
        }

        item.setItemMeta(meta);
        return item;
    }
}
