// static/js/performance-tracking.js

class PerformanceTracker {
    constructor(folderName) {
        this.folderName = folderName;
        this.metrics = {
            frameRates: [],
            renderTimes: [],
            memoryUsage: [],
            startTime: performance.now(),
            interactionEvents: []
        };
        this.isTracking = false;
        this.setupInteractionTracking();
    }

    setupInteractionTracking() {
        // Track user interactions with the 3D model
        const plotContainer = document.getElementById('plot-container');
        if (plotContainer) {
            const interactions = ['mousedown', 'mouseup', 'mousemove', 'wheel'];
            interactions.forEach(eventType => {
                plotContainer.addEventListener(eventType, () => {
                    this.recordInteraction(eventType);
                });
            });
        }
    }

    recordInteraction(type) {
        if (!this.isTracking) return;
        
        this.metrics.interactionEvents.push({
            type,
            timestamp: performance.now(),
            frameRate: this.getCurrentFrameRate()
        });
    }

    getCurrentFrameRate() {
        // Get the most recent frame rate measurement
        const recentRates = this.metrics.frameRates.slice(-5);
        return recentRates.length > 0 ? 
            recentRates.reduce((sum, rate) => sum + rate, 0) / recentRates.length : 
            null;
    }

    estimateModelComplexity() {
        // Estimate model complexity based on rendering performance
        const avgFrameRate = this.getAverageFrameRate();
        const avgRenderTime = this.getAverageRenderTime();
        
        // Calculate complexity score (0-100)
        const frameRateScore = Math.max(0, Math.min(100, (60 - avgFrameRate) * 1.67));
        const renderTimeScore = Math.max(0, Math.min(100, avgRenderTime / 2));
        
        return Math.round((frameRateScore + renderTimeScore) / 2);
    }

    getAverageFrameRate() {
        return this.metrics.frameRates.length > 0 ?
            this.metrics.frameRates.reduce((sum, rate) => sum + rate, 0) / this.metrics.frameRates.length :
            0;
    }

    getAverageRenderTime() {
        return this.metrics.renderTimes.length > 0 ?
            this.metrics.renderTimes.reduce((sum, time) => sum + time, 0) / this.metrics.renderTimes.length :
            0;
    }

    async submitMetrics() {
        try {
            const averageMetrics = this.calculateAverageMetrics();
            const response = await fetch('/api/metrics/performance', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    folder_name: this.folderName,
                    metrics: averageMetrics,
                    interaction_data: this.analyzeInteractions(),
                    load_metrics: this.metrics.initialLoad
                })
            });

            if (!response.ok) {
                throw new Error('Failed to submit metrics');
            }

            const result = await response.json();
            if (result.recommendations) {
                this.displayRecommendations(result.recommendations);
            }
        } catch (error) {
            console.error('Error submitting metrics:', error);
        }
    }

    analyzeInteractions() {
        // Analyze user interaction patterns
        const interactions = this.metrics.interactionEvents;
        if (interactions.length === 0) return null;

        const interactionsByType = {};
        interactions.forEach(event => {
            if (!interactionsByType[event.type]) {
                interactionsByType[event.type] = [];
            }
            interactionsByType[event.type].push(event);
        });

        return Object.entries(interactionsByType).map(([type, events]) => ({
            type,
            count: events.length,
            avgFrameRate: events.reduce((sum, e) => sum + (e.frameRate || 0), 0) / events.length,
            timeDistribution: this.calculateTimeDistribution(events)
        }));
    }

    calculateTimeDistribution(events) {
        // Calculate how interactions are distributed over time
        const duration = this.metrics.startTime - performance.now();
        const segments = 10; // Split into 10 time segments
        const segmentDuration = duration / segments;
        
        const distribution = new Array(segments).fill(0);
        
        events.forEach(event => {
            const segment = Math.floor((event.timestamp - this.metrics.startTime) / segmentDuration);
            if (segment >= 0 && segment < segments) {
                distribution[segment]++;
            }
        });

        return distribution;
    }

    displayRecommendations(recommendations) {
        // Create or update recommendations display
        let container = document.getElementById('performance-recommendations');
        if (!container) {
            container = document.createElement('div');
            container.id = 'performance-recommendations';
            container.className = 'performance-recommendations';
            document.querySelector('.visualization-section').appendChild(container);
        }

        container.innerHTML = `
            <h3>Performance Recommendations</h3>
            <ul>
                ${recommendations.map(rec => `
                    <li class="recommendation ${rec.severity}">
                        <strong>${rec.type}:</strong> ${rec.message}
                    </li>
                `).join('')}
            </ul>
        `;
    }
}

// Export the tracker for use in other modules
export default PerformanceTracker;