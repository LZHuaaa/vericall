/**
 * API Key Manager Module
 * Manages multiple API keys and rotates them on rate limit errors
 */

export interface KeyStatus {
    key: string;
    isActive: boolean;
    isExhausted: boolean;
    exhaustedAt?: Date;
    usageCount: number;
    lastError?: string;
}

export class ApiKeyManager {
    private keys: KeyStatus[] = [];
    private currentIndex: number = 0;
    private onKeyRotated: (newIndex: number, totalKeys: number) => void = () => { };
    private onAllKeysExhausted: () => void = () => { };

    // Callback for UI updates
    public setOnKeyRotated(callback: (newIndex: number, totalKeys: number) => void): void {
        this.onKeyRotated = callback;
    }

    public setOnAllKeysExhausted(callback: () => void): void {
        this.onAllKeysExhausted = callback;
    }

    /**
     * Initialize with API keys (from environment or direct input)
     * Keys can be comma-separated in a single env var or multiple env vars
     */
    public initialize(keys: string[]): void {
        this.keys = keys
            .filter(k => k && k.trim().length > 0)
            .map(key => ({
                key: key.trim(),
                isActive: false,
                isExhausted: false,
                usageCount: 0
            }));

        if (this.keys.length > 0) {
            this.keys[0].isActive = true;
            console.log(`🔑 ApiKeyManager: Initialized with ${this.keys.length} API key(s)`);
        } else {
            console.warn('⚠️ ApiKeyManager: No API keys provided!');
        }
    }

    /**
     * Load keys from environment variable (comma-separated)
     * For Vite: VITE_API_KEY=key1,key2,key3,key4,key5
     * Can also check API_KEY for backward compatibility
     */
    public loadFromEnv(): void {
        // Vite uses import.meta.env with VITE_ prefix
        // @ts-ignore - import.meta.env is Vite-specific
        const viteKey = typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_KEY;
        // Fallback to process.env for Node/other environments
        const processKey = typeof process !== 'undefined' && process.env?.API_KEY;

        const envKey = viteKey || processKey || '';

        if (!envKey) {
            console.warn('⚠️ No API key found! Make sure .env.local has VITE_API_KEY=your_key');
            console.warn('   For multiple keys: VITE_API_KEY=key1,key2,key3');
        }

        const keys = envKey.split(',').map((k: string) => k.trim()).filter((k: string) => k.length > 0);
        this.initialize(keys);
    }

    /**
     * Get the current active API key
     */
    public getCurrentKey(): string {
        const activeKey = this.keys.find(k => k.isActive && !k.isExhausted);
        if (activeKey) {
            activeKey.usageCount++;
            return activeKey.key;
        }

        // Try to find any non-exhausted key
        const availableKey = this.keys.find(k => !k.isExhausted);
        if (availableKey) {
            availableKey.isActive = true;
            availableKey.usageCount++;
            return availableKey.key;
        }

        console.error('❌ All API keys exhausted!');
        this.onAllKeysExhausted();
        return '';
    }

    /**
     * Mark the current key as exhausted and rotate to next
     * Called when a 429 rate limit error is encountered
     */
    public rotateOnError(errorMessage?: string): string {
        // Mark current key as exhausted
        const currentKey = this.keys[this.currentIndex];
        if (currentKey) {
            currentKey.isExhausted = true;
            currentKey.isActive = false;
            currentKey.exhaustedAt = new Date();
            currentKey.lastError = errorMessage;
            console.log(`🔄 Key ${this.currentIndex + 1}/${this.keys.length} exhausted`);
        }

        // Find next available key
        const originalIndex = this.currentIndex;
        do {
            this.currentIndex = (this.currentIndex + 1) % this.keys.length;

            // Check if we've cycled through all keys
            if (this.currentIndex === originalIndex) {
                console.error('❌ All API keys exhausted! No more keys available.');
                this.onAllKeysExhausted();
                return '';
            }
        } while (this.keys[this.currentIndex].isExhausted);

        // Activate the new key
        const newKey = this.keys[this.currentIndex];
        newKey.isActive = true;

        console.log(`✅ Rotated to key ${this.currentIndex + 1}/${this.keys.length}`);
        this.onKeyRotated(this.currentIndex + 1, this.keys.length);

        return newKey.key;
    }

    /**
     * Reset all exhausted keys (for manual recovery)
     * Useful when quotas have reset
     */
    public resetAllKeys(): void {
        this.keys.forEach(k => {
            k.isExhausted = false;
            k.lastError = undefined;
            k.exhaustedAt = undefined;
        });
        this.currentIndex = 0;
        if (this.keys.length > 0) {
            this.keys.forEach(k => k.isActive = false);
            this.keys[0].isActive = true;
        }
        console.log('🔄 All API keys reset');
    }

    /**
     * Get status of all keys (for UI display)
     */
    public getKeyStatuses(): { index: number; status: 'active' | 'exhausted' | 'available'; usageCount: number }[] {
        return this.keys.map((k, i) => ({
            index: i + 1,
            status: k.isActive && !k.isExhausted ? 'active' : k.isExhausted ? 'exhausted' : 'available',
            usageCount: k.usageCount
        }));
    }

    /**
     * Get count of available keys
     */
    public getAvailableKeyCount(): number {
        return this.keys.filter(k => !k.isExhausted).length;
    }

    /**
     * Get total key count
     */
    public getTotalKeyCount(): number {
        return this.keys.length;
    }

    /**
     * Get current key index (1-based for display)
     */
    public getCurrentKeyIndex(): number {
        return this.currentIndex + 1;
    }

    /**
     * Check if a specific error is a rate limit error
     */
    public static isRateLimitError(error: any): boolean {
        if (!error) return false;

        // Check for 429 status code
        if (error.status === 429 || error.code === 429) return true;

        // Check error message
        const message = error.message || error.toString();
        return message.includes('429') ||
            message.includes('RESOURCE_EXHAUSTED') ||
            message.includes('quota') ||
            message.includes('rate limit');
    }
}

// Export singleton
export const apiKeyManager = new ApiKeyManager();
