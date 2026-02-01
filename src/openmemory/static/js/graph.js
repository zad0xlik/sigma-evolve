// Graph Visualization Component for Project-Pattern Relationships
import { api } from '/static/js/api.js';
import { utils } from '/static/js/utils.js';

export function graphVisualization() {
    return {
        // State
        graphData: null,
        loading: false,
        network: null,
        containerReady: false,
        
        // Init
        async init() {
            console.log('Graph visualization initialized');
            await this.loadGraphData();
        },
        
        // Load graph data from API
        async loadGraphData() {
            this.loading = true;
            try {
                this.graphData = await api.getProjectPatternGraph();
                console.log('Graph data loaded:', this.graphData);
                
                // Wait for container to be ready
                await this.$nextTick();
                this.renderGraph();
            } catch (error) {
                console.error('Error loading graph data:', error);
                utils.error('Failed to load graph visualization');
            } finally {
                this.loading = false;
            }
        },
        
        // Render the graph using basic SVG
        renderGraph() {
            const container = document.getElementById('graph-container');
            if (!container) {
                console.error('Graph container not found');
                return;
            }
            
            if (!this.graphData || !this.graphData.nodes || this.graphData.nodes.length === 0) {
                container.innerHTML = '<div class="loading">No graph data available</div>';
                return;
            }
            
            // Clear previous content
            container.innerHTML = '';
            
            // Create SVG
            const width = container.clientWidth || 800;
            const height = 600;
            
            const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            svg.setAttribute('width', width);
            svg.setAttribute('height', height);
            svg.style.border = '1px solid #ddd';
            svg.style.borderRadius = '8px';
            svg.style.background = '#fafafa';
            
            container.appendChild(svg);
            
            // Simple force-directed layout simulation
            const nodes = this.graphData.nodes.map(n => ({
                ...n,
                x: Math.random() * (width - 100) + 50,
                y: Math.random() * (height - 100) + 50,
                vx: 0,
                vy: 0
            }));
            
            const edges = this.graphData.edges;
            
            // Create node lookup
            const nodeMap = {};
            nodes.forEach(n => nodeMap[n.id] = n);
            
            // Draw edges
            const edgeGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            edgeGroup.setAttribute('class', 'edges');
            svg.appendChild(edgeGroup);
            
            edges.forEach(edge => {
                const source = nodeMap[edge.source];
                const target = nodeMap[edge.target];
                
                if (source && target) {
                    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                    line.setAttribute('x1', source.x);
                    line.setAttribute('y1', source.y);
                    line.setAttribute('x2', target.x);
                    line.setAttribute('y2', target.y);
                    line.setAttribute('stroke', edge.type === 'applied' ? '#28a745' : '#6c757d');
                    line.setAttribute('stroke-width', edge.type === 'applied' ? '2' : '1');
                    line.setAttribute('stroke-dasharray', edge.type === 'opportunity' ? '5,5' : '0');
                    line.setAttribute('opacity', '0.6');
                    edgeGroup.appendChild(line);
                }
            });
            
            // Draw nodes
            const nodeGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            nodeGroup.setAttribute('class', 'nodes');
            svg.appendChild(nodeGroup);
            
            nodes.forEach(node => {
                // Node circle
                const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                circle.setAttribute('cx', node.x);
                circle.setAttribute('cy', node.y);
                circle.setAttribute('r', node.type === 'project' ? 20 : 15);
                circle.setAttribute('fill', node.type === 'project' ? '#007bff' : '#28a745');
                circle.setAttribute('stroke', '#fff');
                circle.setAttribute('stroke-width', '2');
                circle.style.cursor = 'pointer';
                
                // Tooltip
                const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
                title.textContent = `${node.label}\nType: ${node.type}\n${
                    node.data.confidence ? `Confidence: ${(node.data.confidence * 100).toFixed(0)}%` : ''
                }`;
                circle.appendChild(title);
                
                nodeGroup.appendChild(circle);
                
                // Node label
                const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                text.setAttribute('x', node.x);
                text.setAttribute('y', node.y + (node.type === 'project' ? 30 : 25));
                text.setAttribute('text-anchor', 'middle');
                text.setAttribute('font-size', '12');
                text.setAttribute('font-weight', 'bold');
                text.setAttribute('fill', '#333');
                text.textContent = node.label.length > 15 ? node.label.substring(0, 12) + '...' : node.label;
                
                const textTitle = document.createElementNS('http://www.w3.org/2000/svg', 'title');
                textTitle.textContent = node.label;
                text.appendChild(textTitle);
                
                nodeGroup.appendChild(text);
            });
            
            // Add legend
            this.addLegend(container, width);
            
            // Add metadata info
            this.addMetadata(container);
        },
        
        // Add legend
        addLegend(container, width) {
            const legend = document.createElement('div');
            legend.style.cssText = 'position: absolute; top: 10px; right: 10px; background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);';
            
            legend.innerHTML = `
                <div style="font-weight: bold; margin-bottom: 10px;">Legend</div>
                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <div style="width: 20px; height: 20px; background: #007bff; border-radius: 50%; margin-right: 8px;"></div>
                    <span>Projects</span>
                </div>
                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <div style="width: 15px; height: 15px; background: #28a745; border-radius: 50%; margin-right: 8px;"></div>
                    <span>Patterns</span>
                </div>
                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <div style="width: 30px; height: 2px; background: #6c757d; margin-right: 8px;"></div>
                    <span>Generates</span>
                </div>
                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <div style="width: 30px; height: 2px; background: #28a745; margin-right: 8px;"></div>
                    <span>Applied</span>
                </div>
                <div style="display: flex; align-items: center;">
                    <div style="width: 30px; height: 2px; background: #6c757d; border-top: 2px dashed #6c757d; margin-right: 8px;"></div>
                    <span>Opportunity</span>
                </div>
            `;
            
            container.appendChild(legend);
        },
        
        // Add metadata info
        addMetadata(container) {
            if (!this.graphData || !this.graphData.metadata) return;
            
            const meta = this.graphData.metadata;
            const info = document.createElement('div');
            info.style.cssText = 'position: absolute; bottom: 10px; left: 10px; background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);';
            
            info.innerHTML = `
                <div style="font-weight: bold; margin-bottom: 10px;">Graph Statistics</div>
                <div style="margin-bottom: 5px;"><strong>Projects:</strong> ${meta.total_projects}</div>
                <div style="margin-bottom: 5px;"><strong>Patterns:</strong> ${meta.total_patterns}</div>
                <div style="margin-bottom: 5px;"><strong>Connections:</strong> ${meta.total_connections}</div>
                <div style="font-size: 11px; color: #666; margin-top: 10px;">Last updated: ${new Date(meta.timestamp).toLocaleTimeString()}</div>
            `;
            
            container.appendChild(info);
        },
        
        // Refresh graph data
        async refresh() {
            await this.loadGraphData();
            utils.info('Graph refreshed');
        }
    };
}

// Register globally
window.graphVisualization = graphVisualization;
