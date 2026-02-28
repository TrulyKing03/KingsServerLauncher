package com.battlepass.plugin.gui;

import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.InventoryHolder;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public final class BattlePassHolder implements InventoryHolder {

    private final UUID viewer;
    private final int page;
    private final int maxPage;
    private final Map<Integer, Integer> slotToTier;
    private final List<Integer> visibleTiers;
    private Inventory inventory;

    public BattlePassHolder(UUID viewer, int page, int maxPage, Map<Integer, Integer> slotToTier, List<Integer> visibleTiers) {
        this.viewer = viewer;
        this.page = page;
        this.maxPage = maxPage;
        this.slotToTier = slotToTier;
        this.visibleTiers = visibleTiers;
    }

    @Override
    public Inventory getInventory() {
        return inventory;
    }

    public void setInventory(Inventory inventory) {
        this.inventory = inventory;
    }

    public UUID getViewer() {
        return viewer;
    }

    public int getPage() {
        return page;
    }

    public int getMaxPage() {
        return maxPage;
    }

    public Integer getTierForSlot(int slot) {
        return slotToTier.get(slot);
    }

    public Map<Integer, Integer> getSlotToTier() {
        return Collections.unmodifiableMap(slotToTier);
    }

    public List<Integer> getVisibleTiers() {
        return Collections.unmodifiableList(visibleTiers);
    }
}
