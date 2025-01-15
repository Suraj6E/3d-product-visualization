// static/js/analytics-dashboard.js

class AnalyticsDashboard {
    constructor() {
        this.initialize();
    }

    async initialize() {
        // Fetch initial data
        await this.fetchMetricsData();
        
        // Set up event listeners
        document.getElementById('update-range').addEventListener('click', () => {
            this.updateDateRange();
        });
    }

    async fetchMetricsData() {
        try {
            const startDate = document.getElementById('start-date').value;
            const endDate = document.getElementById('end-date').value;
            
            const response = await fetch(`/api/metrics/dashboard?start=${startDate}&end=${endDate}`);
            const data = await response.json();
            
            this.renderCharts(data);
        } catch (error) {
            console.error('Error fetching metrics:', error);
        }
    }

    renderCharts(data) {
        this.createPerformanceChart(data.performance_metrics);
        this.createResourceChart(data.resource_metrics);
        this.createEngagementChart(data.engagement_stats);
    }

    createPerformanceChart(data) {
        const trace = {
            x: data.map(d => d.folder_name),
            y: data.map(d => d.avg_duration/1000),
            type: 'bar',
            name: 'Average Duration (s)'
        };

        const layout = {
            title: 'Performance by Product',
            xaxis: { title: 'Product' },
            yaxis: { title: 'Average Duration (seconds)' }
        };

        Plotly.newPlot('performance-chart', [trace], layout);
    }

    createResourceChart(data) {
        // Implementation similar to performance chart
    }

    createEngagementChart(data) {
        // Implementation similar to performance chart
    }

    async updateDateRange() {
        await this.fetchMetricsData();
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new AnalyticsDashboard();
});