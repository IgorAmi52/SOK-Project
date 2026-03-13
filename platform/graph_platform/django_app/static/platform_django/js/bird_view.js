(function() {
    function initBirdView(options) {
        const mainViewId = options && options.mainViewId ? options.mainViewId : "main-view";
        const birdSvgId = options && options.birdSvgId ? options.birdSvgId : "bird-view-svg";

        const mainView = document.getElementById(mainViewId);
        const birdSvgElement = document.getElementById(birdSvgId);
        const visualizerContainer = options && options.visualizerContainer
            ? options.visualizerContainer
            : (mainView
                ? mainView.querySelector(".simple-visualizer-container, .block-visualizer-container")
                : null);

        if (!mainView || !birdSvgElement || !window.d3) {
            return;
        }

        const svg = d3.select(birdSvgElement);
        svg.selectAll("*").remove();

        const edgeLayer = svg.append("g").attr("class", "bird-edges");
        const nodeLayer = svg.append("g").attr("class", "bird-nodes");
        const viewportRect = svg.append("rect")
            .attr("class", "viewport-rect")
            .style("cursor", "grab")
            .style("display", "none");
        const emptyLabel = svg.append("text")
            .attr("x", 18)
            .attr("y", 28)
            .attr("fill", "#61738d")
            .attr("font-size", 11)
            .attr("font-family", "system-ui, sans-serif")
            .text("No graph loaded")
            .style("display", "none");

        let currentState = null;
        let projection = null;
        let dragState = null;

        function getSvgSize() {
            const rect = birdSvgElement.getBoundingClientRect();
            return {
                width: Math.max(1, Math.floor(rect.width || birdSvgElement.clientWidth || 260)),
                height: Math.max(1, Math.floor(rect.height || birdSvgElement.clientHeight || 180)),
            };
        }

        function projectNodeSize(nodeDatum) {
            return {
                halfWidth: (nodeDatum.width || 30) / 2,
                halfHeight: (nodeDatum.height || 30) / 2,
            };
        }

        function buildProjection(nodes, svgWidth, svgHeight) {
            if (!nodes || nodes.length === 0) {
                return null;
            }

            let minX = Infinity;
            let minY = Infinity;
            let maxX = -Infinity;
            let maxY = -Infinity;

            for (const nodeDatum of nodes) {
                const size = projectNodeSize(nodeDatum);
                minX = Math.min(minX, nodeDatum.x - size.halfWidth);
                minY = Math.min(minY, nodeDatum.y - size.halfHeight);
                maxX = Math.max(maxX, nodeDatum.x + size.halfWidth);
                maxY = Math.max(maxY, nodeDatum.y + size.halfHeight);
            }

            const padding = 12;
            const graphWidth = Math.max(1, maxX - minX);
            const graphHeight = Math.max(1, maxY - minY);
            const scale = Math.max(
                0.01,
                Math.min((svgWidth - (padding * 2)) / graphWidth, (svgHeight - (padding * 2)) / graphHeight)
            );
            const offsetX = (svgWidth - (graphWidth * scale)) / 2;
            const offsetY = (svgHeight - (graphHeight * scale)) / 2;

            return {
                minX,
                minY,
                scale,
                offsetX,
                offsetY,
            };
        }

        function worldToBird(x, y) {
            return {
                x: projection.offsetX + ((x - projection.minX) * projection.scale),
                y: projection.offsetY + ((y - projection.minY) * projection.scale),
            };
        }

        function birdToWorld(x, y) {
            return {
                x: projection.minX + ((x - projection.offsetX) / projection.scale),
                y: projection.minY + ((y - projection.offsetY) / projection.scale),
            };
        }

        function focusNode(nodeId) {
            if (!currentState || !nodeId) {
                return;
            }

            const nodeDatum = currentState.nodes.find((item) => item.id === nodeId);
            if (!nodeDatum) {
                return;
            }

            if (visualizerContainer && visualizerContainer.focusNode) {
                visualizerContainer.focusNode(nodeId);
            }

            mainView.dispatchEvent(new CustomEvent("visualizer:select", {
                detail: {
                    nodeId: nodeId,
                    node: nodeDatum,
                },
                bubbles: true,
            }));
        }

        function setViewportTransform(transform, animate) {
            if (!visualizerContainer || !visualizerContainer.setViewTransform) {
                return;
            }
            visualizerContainer.setViewTransform(transform, animate);
        }

        function centerOnBirdPoint(pointerX, pointerY) {
            if (!currentState || !projection) {
                return;
            }

            const canvas = currentState.canvas || { width: 1, height: 1 };
            const transform = currentState.transform || { x: 0, y: 0, k: 1 };
            const worldPoint = birdToWorld(pointerX, pointerY);

            setViewportTransform(
                {
                    x: (canvas.width / 2) - (worldPoint.x * transform.k),
                    y: (canvas.height / 2) - (worldPoint.y * transform.k),
                    k: transform.k,
                },
                true
            );
        }

        function updateViewportRect() {
            if (!currentState || !projection) {
                viewportRect.style("display", "none");
                return;
            }

            const transform = currentState.transform || { x: 0, y: 0, k: 1 };
            const canvas = currentState.canvas || { width: 1, height: 1 };
            const scale = transform.k || 1;

            const topLeft = worldToBird((-transform.x) / scale, (-transform.y) / scale);
            const bottomRight = worldToBird(
                (canvas.width - transform.x) / scale,
                (canvas.height - transform.y) / scale
            );

            viewportRect
                .style("display", null)
                .attr("x", Math.min(topLeft.x, bottomRight.x))
                .attr("y", Math.min(topLeft.y, bottomRight.y))
                .attr("width", Math.abs(bottomRight.x - topLeft.x))
                .attr("height", Math.abs(bottomRight.y - topLeft.y));
        }

        function render(state) {
            currentState = state && Array.isArray(state.nodes) ? state : null;
            const svgSize = getSvgSize();

            svg.attr("viewBox", "0 0 " + svgSize.width + " " + svgSize.height);

            if (!currentState || currentState.nodes.length === 0) {
                edgeLayer.selectAll("*").remove();
                nodeLayer.selectAll("*").remove();
                viewportRect.style("display", "none");
                emptyLabel.style("display", null);
                return;
            }

            emptyLabel.style("display", "none");
            projection = buildProjection(currentState.nodes, svgSize.width, svgSize.height);
            if (!projection) {
                return;
            }

            const nodesById = new Map(currentState.nodes.map((nodeDatum) => [nodeDatum.id, nodeDatum]));
            const edgeData = (currentState.edges || [])
                .map((edgeDatum) => {
                    const source = nodesById.get(edgeDatum.sourceId);
                    const target = nodesById.get(edgeDatum.targetId);
                    if (!source || !target) {
                        return null;
                    }
                    return {
                        id: edgeDatum.id,
                        source: source,
                        target: target,
                    };
                })
                .filter(Boolean);

            edgeLayer.selectAll("line")
                .data(edgeData, (edgeDatum) => edgeDatum.id)
                .join("line")
                .attr("stroke", "#526274")
                .attr("stroke-width", 1)
                .attr("x1", (edgeDatum) => worldToBird(edgeDatum.source.x, edgeDatum.source.y).x)
                .attr("y1", (edgeDatum) => worldToBird(edgeDatum.source.x, edgeDatum.source.y).y)
                .attr("x2", (edgeDatum) => worldToBird(edgeDatum.target.x, edgeDatum.target.y).x)
                .attr("y2", (edgeDatum) => worldToBird(edgeDatum.target.x, edgeDatum.target.y).y);

            nodeLayer.selectAll("circle")
                .data(currentState.nodes, (nodeDatum) => nodeDatum.id)
                .join("circle")
                .attr("cx", (nodeDatum) => worldToBird(nodeDatum.x, nodeDatum.y).x)
                .attr("cy", (nodeDatum) => worldToBird(nodeDatum.x, nodeDatum.y).y)
                .attr("r", (nodeDatum) => {
                    const longestSide = Math.max(nodeDatum.width || 30, nodeDatum.height || 30);
                    return Math.max(3, Math.min(8, longestSide * projection.scale * 0.18));
                })
                .attr("fill", (nodeDatum) => (
                    nodeDatum.id === currentState.selectedNodeId ? "#ff6b6b" : "#8ca3b9"
                ))
                .attr("stroke", (nodeDatum) => (
                    nodeDatum.id === currentState.selectedNodeId ? "#c0392b" : "#243447"
                ))
                .attr("stroke-width", 1.2)
                .style("cursor", "pointer")
                .on("click", function(event, nodeDatum) {
                    event.stopPropagation();
                    focusNode(nodeDatum.id);
                });

            updateViewportRect();
        }

        function handleStateEvent(event) {
            render(event.detail);
        }

        function stopDragging() {
            if (!dragState) {
                return;
            }

            dragState = null;
            viewportRect.style("cursor", "grab");
            window.removeEventListener("pointermove", onPointerMove);
            window.removeEventListener("pointerup", stopDragging);
        }

        function onPointerMove(event) {
            if (!dragState || !projection || !currentState) {
                return;
            }

            const deltaBirdX = event.clientX - dragState.startClientX;
            const deltaBirdY = event.clientY - dragState.startClientY;
            const deltaWorldX = deltaBirdX / projection.scale;
            const deltaWorldY = deltaBirdY / projection.scale;

            setViewportTransform(
                {
                    x: dragState.startTransformX - (deltaWorldX * dragState.scale),
                    y: dragState.startTransformY - (deltaWorldY * dragState.scale),
                    k: dragState.scale,
                },
                false
            );
        }

        viewportRect.on("pointerdown", function(event) {
            if (!currentState) {
                return;
            }

            const transform = currentState.transform || { x: 0, y: 0, k: 1 };
            dragState = {
                startClientX: event.clientX,
                startClientY: event.clientY,
                startTransformX: transform.x,
                startTransformY: transform.y,
                scale: transform.k,
            };

            viewportRect.style("cursor", "grabbing");
            event.preventDefault();
            event.stopPropagation();
            window.addEventListener("pointermove", onPointerMove);
            window.addEventListener("pointerup", stopDragging);
        });

        svg.on("click", function(event) {
            if (!projection) {
                return;
            }

            const pointer = d3.pointer(event, birdSvgElement);
            centerOnBirdPoint(pointer[0], pointer[1]);
        });

        window.addEventListener("resize", function() {
            if (currentState) {
                render(currentState);
            }
        });

        mainView.addEventListener("visualizer:state", handleStateEvent);

        if (visualizerContainer && visualizerContainer.getViewState) {
            render(visualizerContainer.getViewState());
            return;
        }

        render(null);
    }

    window.BirdView = {
        init: initBirdView,
    };
})();
