package com.battlepass.plugin.model;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public final class Tier {

    private final int number;
    private final long requiredXp;
    private final String material;
    private final int amount;
    private final String name;
    private final List<String> lore;
    private final int customModelData;
    private final boolean glint;
    private final List<String> flags;
    private final List<String> freeRewards;
    private final List<String> premiumRewards;
    private final List<String> freePreview;
    private final List<String> premiumPreview;

    public Tier(int number,
                long requiredXp,
                String material,
                int amount,
                String name,
                List<String> lore,
                int customModelData,
                boolean glint,
                List<String> flags,
                List<String> freeRewards,
                List<String> premiumRewards,
                List<String> freePreview,
                List<String> premiumPreview) {
        this.number = number;
        this.requiredXp = requiredXp;
        this.material = material;
        this.amount = amount;
        this.name = name;
        this.lore = new ArrayList<>(lore);
        this.customModelData = customModelData;
        this.glint = glint;
        this.flags = new ArrayList<>(flags);
        this.freeRewards = new ArrayList<>(freeRewards);
        this.premiumRewards = new ArrayList<>(premiumRewards);
        this.freePreview = new ArrayList<>(freePreview);
        this.premiumPreview = new ArrayList<>(premiumPreview);
    }

    public int getNumber() {
        return number;
    }

    public long getRequiredXp() {
        return requiredXp;
    }

    public String getMaterial() {
        return material;
    }

    public int getAmount() {
        return amount;
    }

    public String getName() {
        return name;
    }

    public List<String> getLore() {
        return Collections.unmodifiableList(lore);
    }

    public int getCustomModelData() {
        return customModelData;
    }

    public boolean isGlint() {
        return glint;
    }

    public List<String> getFlags() {
        return Collections.unmodifiableList(flags);
    }

    public List<String> getFreeRewards() {
        return Collections.unmodifiableList(freeRewards);
    }

    public List<String> getPremiumRewards() {
        return Collections.unmodifiableList(premiumRewards);
    }

    public List<String> getFreePreview() {
        return Collections.unmodifiableList(freePreview);
    }

    public List<String> getPremiumPreview() {
        return Collections.unmodifiableList(premiumPreview);
    }
}
