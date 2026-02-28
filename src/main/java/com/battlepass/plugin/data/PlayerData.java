package com.battlepass.plugin.data;

import java.util.HashSet;
import java.util.Set;
import java.util.UUID;

public final class PlayerData {

    private final UUID uuid;
    private long xp;
    private boolean premiumOwned;
    private final Set<Integer> claimedFree;
    private final Set<Integer> claimedPremium;

    public PlayerData(UUID uuid) {
        this.uuid = uuid;
        this.claimedFree = new HashSet<>();
        this.claimedPremium = new HashSet<>();
    }

    public UUID getUuid() {
        return uuid;
    }

    public long getXp() {
        return xp;
    }

    public void setXp(long xp) {
        this.xp = Math.max(0, xp);
    }

    public void addXp(long amount) {
        if (amount <= 0) {
            return;
        }
        this.xp += amount;
    }

    public boolean isPremiumOwned() {
        return premiumOwned;
    }

    public void setPremiumOwned(boolean premiumOwned) {
        this.premiumOwned = premiumOwned;
    }

    public Set<Integer> getClaimedFree() {
        return claimedFree;
    }

    public Set<Integer> getClaimedPremium() {
        return claimedPremium;
    }

    public boolean hasClaimed(int tier, com.battlepass.plugin.model.RewardTrack track) {
        return track == com.battlepass.plugin.model.RewardTrack.FREE
                ? claimedFree.contains(tier)
                : claimedPremium.contains(tier);
    }

    public void setClaimed(int tier, com.battlepass.plugin.model.RewardTrack track) {
        if (track == com.battlepass.plugin.model.RewardTrack.FREE) {
            claimedFree.add(tier);
        } else {
            claimedPremium.add(tier);
        }
    }
}
