// src/components/tabs/GraphTab.tsx
import { useEffect, useMemo, useRef, useState, Suspense, lazy, useLayoutEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { Progress } from "../ui/progress";
import { BarChart3, RefreshCw } from "lucide-react";
import { kgFileNodeLink, type NodeLinkGraph } from "../../api";
import { useStore } from "../../store";

const ForceGraph2D = lazy(() => import("react-force-graph-2d"));

export function GraphTab() {
  const { selectedDoc } = useStore();
  const [graph, setGraph] = useState<NodeLinkGraph | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const fgRef = useRef<any>(null);

  const filename = selectedDoc?.summary_filename;

  useEffect(() => {
    if (!filename) {
      setGraph(null);
      setErr(null);
      return;
    }
    setLoading(true);
    setErr(null);

    // strip "summary/" if your backend expects a bare filename
    const cleanFilename = filename.startsWith("summary/") ? filename.slice(8) : filename;

    kgFileNodeLink({ file: cleanFilename }) // <— use "filename" key as per api.ts
      .then((g) => setGraph(g))
      .catch((e: any) => setErr(String(e?.message || e)))
      .finally(() => setLoading(false));
  }, [filename]);

  const stats = useMemo(() => {
    if (!graph) return { nodes: 0, links: 0 };
    return { nodes: graph.nodes?.length ?? 0, links: (graph as any).edges?.length ?? 0 };
  }, [graph]);

  function recenter() {
    if (fgRef.current) fgRef.current.zoomToFit(800, 60);
  }

  // theme-aware colors for canvas
  const isDark =
    typeof document !== "undefined" &&
    (document.documentElement.classList.contains("dark") ||
      document.body.classList.contains("dark"));

  const edgeColor =  "rgba(0, 0, 0, 0.55)"
  const edgeLabelColor = isDark ? "rgba(46, 39, 65, 0.9)" : "rgba(0,0,0,0.9)";
  const nodeFill = isDark ? "#0452b1ff" /* tailwind sky-400 */ : "#2563eb" /* blue-600 */;
  const nodeLabelColor = "#111";

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="grid gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Document Graph
            </CardTitle>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={recenter} disabled={!graph}>
                <RefreshCw className="mr-2 h-4 w-4" />
                Re-center
              </Button>
            </div>
          </CardHeader>

          <CardContent className="space-y-4">
            {!selectedDoc && (
              <div className="text-sm opacity-70">Select a document to view its knowledge graph.</div>
            )}

            {selectedDoc && (
              <>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="text-center p-4 bg-muted rounded-lg">
                    <div className="text-2xl font-bold text-primary">
                      {loading ? "…" : stats.nodes}
                    </div>
                    <div className="text-sm text-muted-foreground">Nodes</div>
                  </div>
                  <div className="text-center p-4 bg-muted rounded-lg">
                    <div className="text-2xl font-bold text-primary">
                      {loading ? "…" : stats.links}
                    </div>
                    <div className="text-sm text-muted-foreground">Edges</div>
                  </div>
                  <div className="text-center p-4 bg-muted rounded-lg">
                    <div className="text-2xl font-bold text-primary">
                      {selectedDoc.title || selectedDoc.id}
                    </div>
                    <div className="text-sm text-muted-foreground">Source document</div>
                  </div>
                </div>

                {loading && (
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>Loading graph…</span>
                      <span>Working</span>
                    </div>
                    <Progress value={66} className="h-2" />
                  </div>
                )}

                {err && <div className="text-sm text-red-600">{err}</div>}

                {!loading && !err && graph && (
                  <div className="rounded-lg border overflow-hidden">
                    <Suspense fallback={<div className="p-4 text-sm opacity-70">Initializing renderer…</div>}>
                      <ForceGraph2D
                        ref={fgRef}
                        graphData={{
                          nodes:
                            graph.nodes?.map((n: any) => ({
                              id: n.id,
                              name: n.label || n.id,
                              group: n.group,
                              ...n,
                            })) ?? [],
                          // ✅ your API returns "edges"
                          links:
                            (graph as any).edges?.map((l: any) => ({
                              source: l.source,
                              target: l.target,
                              label: l.predicate,
                              ...l,
                            })) ?? [],
                        }}
                        width={1000}
                        height={600}
                        cooldownTicks={60}
                        onEngineStop={recenter}
                        // Make links clearly visible
                        linkColor={() => edgeColor}
                        linkWidth={() => 1.5}
                        linkDirectionalArrowLength={6}
                        linkDirectionalArrowRelPos={0.55}
                        // Draw edge labels (predicates) at midpoints
                        linkCanvasObject={(link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
                          const label: string =
                            link.label || link.predicate || `${link.source?.id ?? link.source} → ${link.target?.id ?? link.target}`;
                          if (!label) return;

                          const start = link.source;
                          const end = link.target;
                          if (!start || !end) return;

                          // midpoint
                          const textPos = {
                            x: ((start.x || 0) + (end.x || 0)) / 2,
                            y: ((start.y || 0) + (end.y || 0)) / 2,
                          };

                          const fontSize = Math.max(2, 2 / globalScale);
                          ctx.save();
                          ctx.font = `${fontSize}px Sans-Serif`;
                          ctx.fillStyle = edgeLabelColor;
                          ctx.textAlign = "center";
                          ctx.textBaseline = "middle";

                          // slight outline for readability
                          ctx.lineWidth = 3;
                          ctx.strokeStyle = isDark ? "rgba(0,0,0,0.5)" : "rgba(255,255,255,0.6)";
                          ctx.strokeText(label, textPos.x, textPos.y);

                          ctx.fillText(label, textPos.x, textPos.y);
                          ctx.restore();
                        }}
                        linkCanvasObjectMode={() => "after"}
                        // Custom nodes with labels
                        nodeRelSize={6}
                        nodeCanvasObjectMode={() => "replace"}
                        nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
                          const r = 6;
                          ctx.save();
                          // node circle
                          ctx.beginPath();
                          ctx.arc(node.x || 0, node.y || 0, r, 0, 2 * Math.PI, false);
                          ctx.fillStyle = node.color || nodeFill;
                          ctx.fill();

                          // node label
                          const label = node.name || node.id;
                          const fontSize = Math.max(2, 2 / globalScale);
                          ctx.font = `${fontSize}px Sans-Serif`;
                          ctx.textAlign = "center";
                          ctx.textBaseline = "top";
                          ctx.fillStyle = nodeLabelColor;

                          // outline for readability
                          ctx.lineWidth = 3;
                          ctx.strokeStyle = isDark ? "rgba(0,0,0,0.5)" : "rgba(255,255,255,0.7)";
                          ctx.strokeText(label, node.x || 0, (node.y || 0) + r + 2);

                          ctx.fillText(label, node.x || 0, (node.y || 0) + r + 2);
                          ctx.restore();
                        }}
                        // UX sugar
                        onNodeClick={(node: any) => {
                          if (!fgRef.current) return;
                          const distance = 60;
                          const distRatio = 1 + distance / Math.hypot(node.x || 0, node.y || 0);
                          fgRef.current.centerAt((node.x || 0) / distRatio, (node.y || 0) / distRatio, 800);
                          fgRef.current.zoom(2, 800);
                        }}
                      />
                    </Suspense>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>

        {graph && !loading && !err && (
          <Card>
            <CardHeader>
              <CardTitle>Key Entities</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {(graph.nodes ?? [])
                  .slice(0, 24)
                  .map((n: any) => (
                    <span
                      key={n.id}
                      className="px-3 py-1 bg-primary text-primary-foreground rounded-full text-sm"
                      title={String(n.label || n.id)}
                    >
                      {n.label || n.id}
                    </span>
                  ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
