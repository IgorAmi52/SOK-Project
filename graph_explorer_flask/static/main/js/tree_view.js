(function() {
    const state = {
        container: null,
        rootSelect: null,
        expandAllButton: null,
        collapseButton: null,
        jumpInput: null,
        jumpButton: null,
        jumpOptions: null,
        graphData: null,
        nodeById: new Map(),
        adjacency: new Map(),
        rootNodeId: null,
        selectedNodeId: null,
        expandedNodeIds: new Set(),
    };

    function buildIndex(graphData) {
        state.nodeById = new Map();
        state.adjacency = new Map();

        if (!graphData || !Array.isArray(graphData.nodes) || !Array.isArray(graphData.edges)) {
            return;
        }

        for (const node of graphData.nodes) {
            const normalizedNode = {
                id: node.id,
                attributes: node.attributes || {},
            };
            state.nodeById.set(node.id, normalizedNode);
            state.adjacency.set(node.id, []);
        }

        for (const edge of graphData.edges) {
            if (!state.nodeById.has(edge.source) || !state.nodeById.has(edge.target)) {
                continue;
            }

            state.adjacency.get(edge.source).push({
                nodeId: edge.target,
                edgeId: edge.id,
                directed: edge.directed,
            });

            if (!edge.directed) {
                state.adjacency.get(edge.target).push({
                    nodeId: edge.source,
                    edgeId: edge.id,
                    directed: edge.directed,
                });
            }
        }

        for (const [nodeId, children] of state.adjacency.entries()) {
            children.sort((left, right) => left.nodeId.localeCompare(right.nodeId));
            state.adjacency.set(nodeId, children);
        }
    }

    function setEmptyTree(message) {
        if (!state.container) {
            return;
        }
        state.container.innerHTML = '<div class="tree-empty">' + message + '</div>';
    }

    function getSortedNodeIds() {
        return Array.from(state.nodeById.keys()).sort();
    }

    function renderRootOptions() {
        if (!state.rootSelect) {
            return;
        }

        const nodeIds = getSortedNodeIds();
        state.rootSelect.innerHTML = '';

        if (nodeIds.length === 0) {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No nodes';
            state.rootSelect.appendChild(option);
            state.rootSelect.disabled = true;
            state.rootNodeId = null;
            return;
        }

        state.rootSelect.disabled = false;

        for (const nodeId of nodeIds) {
            const option = document.createElement('option');
            option.value = nodeId;
            option.textContent = nodeId;
            state.rootSelect.appendChild(option);
        }

        if (!state.rootNodeId || !state.nodeById.has(state.rootNodeId)) {
            state.rootNodeId = nodeIds[0];
        }

        state.rootSelect.value = state.rootNodeId;
    }

    function renderJumpOptions() {
        if (!state.jumpOptions) {
            return;
        }

        state.jumpOptions.innerHTML = '';
        const nodeIds = getSortedNodeIds();
        for (const nodeId of nodeIds) {
            const option = document.createElement('option');
            option.value = nodeId;
            state.jumpOptions.appendChild(option);
        }
    }

    function updateExpandButtonsState() {
        const disabled = !state.rootNodeId;
        if (state.expandAllButton) {
            state.expandAllButton.disabled = disabled;
        }
        if (state.collapseButton) {
            state.collapseButton.disabled = disabled;
        }
    }

    function toggleNode(nodeId) {
        if (state.expandedNodeIds.has(nodeId)) {
            state.expandedNodeIds.delete(nodeId);
        } else {
            state.expandedNodeIds.add(nodeId);
        }
        renderTree();
    }

    function getRowByNodeId(nodeId) {
        if (!state.container || !nodeId) {
            return null;
        }

        const rows = state.container.querySelectorAll('.tree-row[data-node-id]');
        for (const row of rows) {
            if (row.dataset.nodeId === nodeId) {
                return row;
            }
        }
        return null;
    }

    function updateSelectedRows() {
        if (!state.container) {
            return;
        }

        const rows = state.container.querySelectorAll('.tree-row[data-node-id]');
        for (const row of rows) {
            const isSelected = row.dataset.nodeId === state.selectedNodeId;
            row.classList.toggle('selected', isSelected);
        }
    }

    function scrollSelectedIntoView() {
        if (!state.selectedNodeId) {
            return;
        }
        const row = getRowByNodeId(state.selectedNodeId);
        if (row) {
            row.scrollIntoView({ block: 'nearest' });
        }
    }

    function findPathFromRoot(targetNodeId) {
        if (!state.rootNodeId || !state.nodeById.has(targetNodeId)) {
            return null;
        }

        const queue = [state.rootNodeId];
        const visited = new Set([state.rootNodeId]);
        const parentByNodeId = new Map();

        while (queue.length > 0) {
            const currentNodeId = queue.shift();
            if (currentNodeId === targetNodeId) {
                break;
            }

            const children = state.adjacency.get(currentNodeId) || [];
            for (const child of children) {
                if (visited.has(child.nodeId)) {
                    continue;
                }
                visited.add(child.nodeId);
                parentByNodeId.set(child.nodeId, currentNodeId);
                queue.push(child.nodeId);
            }
        }

        if (!visited.has(targetNodeId)) {
            return null;
        }

        const path = [targetNodeId];
        let cursor = targetNodeId;
        while (parentByNodeId.has(cursor)) {
            cursor = parentByNodeId.get(cursor);
            path.push(cursor);
        }
        path.reverse();
        return path;
    }

    function expandToDepth(depth) {
        if (!state.rootNodeId || depth < 0) {
            return;
        }

        state.expandedNodeIds = new Set();

        const queue = [{ nodeId: state.rootNodeId, level: 0 }];
        const visited = new Set([state.rootNodeId]);

        while (queue.length > 0) {
            const current = queue.shift();
            const currentChildren = state.adjacency.get(current.nodeId) || [];

            if (current.level < depth && currentChildren.length > 0) {
                state.expandedNodeIds.add(current.nodeId);
            }

            if (current.level >= depth) {
                continue;
            }

            for (const child of currentChildren) {
                if (visited.has(child.nodeId)) {
                    continue;
                }
                visited.add(child.nodeId);
                queue.push({ nodeId: child.nodeId, level: current.level + 1 });
            }
        }
    }

    function collapseAll() {
        state.expandedNodeIds = new Set();
        renderTree();
    }

    function expandAll() {
        if (!state.rootNodeId) {
            return;
        }

        state.expandedNodeIds = new Set();

        const queue = [state.rootNodeId];
        const visited = new Set();

        while (queue.length > 0) {
            const currentNodeId = queue.shift();
            if (visited.has(currentNodeId)) {
                continue;
            }

            visited.add(currentNodeId);
            const children = state.adjacency.get(currentNodeId) || [];
            if (children.length > 0) {
                state.expandedNodeIds.add(currentNodeId);
            }

            for (const child of children) {
                if (!visited.has(child.nodeId)) {
                    queue.push(child.nodeId);
                }
            }
        }

        renderTree();
    }

    function selectNode(nodeId, emitEvent) {
        state.selectedNodeId = nodeId;
        updateSelectedRows();
        scrollSelectedIntoView();

        if (!emitEvent || !state.container || !nodeId) {
            return;
        }

        const node = state.nodeById.get(nodeId) || { id: nodeId, attributes: {} };
        state.container.dispatchEvent(new CustomEvent('tree:select', {
            detail: {
                nodeId: nodeId,
                node: node,
            },
            bubbles: true,
        }));
    }

    function createTreeRow(nodeId, depth, isCycle, forceLeaf) {
        const row = document.createElement('div');
        row.className = 'tree-row';
        if (isCycle) {
            row.classList.add('cycle');
        }
        row.dataset.nodeId = nodeId;
        row.style.paddingLeft = (depth * 14 + 4) + 'px';

        const children = state.adjacency.get(nodeId) || [];
        const canExpand = !forceLeaf && children.length > 0 && !isCycle;

        const toggle = document.createElement('button');
        toggle.className = 'tree-toggle';
        if (!canExpand) {
            toggle.classList.add('empty');
            toggle.type = 'button';
            toggle.textContent = '+';
        } else {
            toggle.type = 'button';
            toggle.textContent = state.expandedNodeIds.has(nodeId) ? '-' : '+';
            toggle.addEventListener('click', function(event) {
                event.stopPropagation();
                toggleNode(nodeId);
            });
        }

        const label = document.createElement('span');
        label.className = 'tree-node-label';
        label.textContent = isCycle ? nodeId + ' (cycle)' : nodeId;

        row.appendChild(toggle);
        row.appendChild(label);
        row.addEventListener('click', function() {
            selectNode(nodeId, true);
        });

        return row;
    }

    function appendNode(container, nodeId, depth, pathSet) {
        const row = createTreeRow(nodeId, depth, false, false);
        container.appendChild(row);

        const children = state.adjacency.get(nodeId) || [];
        const isExpanded = state.expandedNodeIds.has(nodeId);
        if (!isExpanded || children.length === 0) {
            return;
        }

        const nextPathSet = new Set(pathSet);
        nextPathSet.add(nodeId);

        for (const child of children) {
            const childId = child.nodeId;
            if (nextPathSet.has(childId)) {
                container.appendChild(createTreeRow(childId, depth + 1, true, true));
                continue;
            }
            appendNode(container, childId, depth + 1, nextPathSet);
        }
    }

    function renderTree() {
        if (!state.container) {
            return;
        }

        state.container.innerHTML = '';

        if (!state.rootNodeId) {
            setEmptyTree('No tree data available.');
            return;
        }

        if (!state.nodeById.has(state.rootNodeId)) {
            setEmptyTree('No tree data available.');
            return;
        }

        const fragment = document.createDocumentFragment();
        appendNode(fragment, state.rootNodeId, 0, new Set());
        state.container.appendChild(fragment);
        updateSelectedRows();
    }

    function focusNode(nodeId, emitEvent) {
        if (!nodeId || !state.nodeById.has(nodeId)) {
            return false;
        }

        const path = findPathFromRoot(nodeId);
        if (path && path.length > 1) {
            for (let index = 0; index < path.length - 1; index += 1) {
                state.expandedNodeIds.add(path[index]);
            }
            renderTree();
        } else if (state.rootNodeId !== nodeId) {
            state.rootNodeId = nodeId;
            if (state.rootSelect) {
                state.rootSelect.value = nodeId;
            }
            expandToDepth(2);
            renderTree();
        }

        selectNode(nodeId, emitEvent);
        return true;
    }

    function jumpToNode() {
        if (!state.jumpInput) {
            return;
        }

        const nodeId = state.jumpInput.value.trim();
        if (!nodeId) {
            return;
        }

        focusNode(nodeId, true);
    }

    function init(config) {
        state.container = document.getElementById(config.containerId);
        state.rootSelect = document.getElementById(config.rootSelectId);
        state.expandAllButton = config.expandAllButtonId
            ? document.getElementById(config.expandAllButtonId)
            : null;
        state.collapseButton = config.collapseButtonId
            ? document.getElementById(config.collapseButtonId)
            : null;
        state.jumpInput = config.jumpInputId
            ? document.getElementById(config.jumpInputId)
            : null;
        state.jumpButton = config.jumpButtonId
            ? document.getElementById(config.jumpButtonId)
            : null;
        state.jumpOptions = config.jumpOptionsId
            ? document.getElementById(config.jumpOptionsId)
            : null;
        state.graphData = config.graphData || null;
        state.selectedNodeId = null;
        state.expandedNodeIds = new Set();

        if (!state.container || !state.rootSelect) {
            return;
        }

        buildIndex(state.graphData);
        renderRootOptions();
        renderJumpOptions();
        updateExpandButtonsState();

        if (!state.rootNodeId) {
            setEmptyTree('No graph loaded.');
            return;
        }

        expandToDepth(2);

        if (state.expandAllButton) {
            state.expandAllButton.onclick = function() {
                expandAll();
            };
        }

        if (state.collapseButton) {
            state.collapseButton.onclick = function() {
                collapseAll();
            };
        }

        state.rootSelect.onchange = function(event) {
            state.rootNodeId = event.target.value;
            expandToDepth(2);
            updateExpandButtonsState();
            renderTree();
        };

        if (state.jumpButton) {
            state.jumpButton.onclick = function() {
                jumpToNode();
            };
        }

        if (state.jumpInput) {
            state.jumpInput.onkeypress = function(event) {
                if (event.key === 'Enter') {
                    jumpToNode();
                }
            };
        }

        renderTree();
    }

    function setSelectedNode(nodeId) {
        focusNode(nodeId, false);
    }

    window.TreeView = {
        init: init,
        setSelectedNode: setSelectedNode,
    };
})();
