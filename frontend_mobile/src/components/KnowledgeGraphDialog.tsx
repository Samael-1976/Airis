import React, { useState, useEffect, useRef } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { Loader2, Network, Search, X, Edit, Trash2, Save } from "lucide-react";
import { useTranslation } from "@/contexts/TranslationContext";
import { getHeaders } from "@/lib/api";
import { toast } from "sonner";

interface KnowledgeGraphDialogProps {
  serverUrl: string;
  userName: string;
}

interface GraphNode {
  id: string;
  x?: number;
  y?: number;
  z?: number;
  baseX?: number;
  baseY?: number;
  baseZ?: number;
  screenX?: number;
  screenY?: number;
  scale?: number;
}

interface GraphLink {
  source: string;
  target: string;
  label: string;
}

export const KnowledgeGraphDialog = ({ serverUrl, userName }: KnowledgeGraphDialogProps) => {
  const { t } = useTranslation();
  const [isLoading, setIsLoading] = useState(false);
  const [nodes, setNodes] = useState<GraphNode[]>(Array(0));
  const [links, setLinks] = useState<GraphLink[]>(Array(0));
  const [searchQuery, setSearchQuery] = useState("");
  
  // Ref mutabile per la fisica, disaccoppiato dallo stato React per evitare lag e desync
  const physicsNodesRef = useRef<GraphNode[]>(Array(0));
  const selectedNodeRef = useRef<string | null>(null);
  const searchQueryRef = useRef("");

  // --- STATI PER INTERATTIVITÀ 3D CANVAS ---
  const [rotation, setRotation] = useState({ x: 0, y: 0 });
  const rotationRef = useRef({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [hasMoved, setHasMoved] = useState(false); // Per distinguere click da drag
  
  // --- STATI PER DIALOGO NODO ---
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [isNodeDialogOpen, setIsNodeDialogOpen] = useState(false);
  const [editNodeName, setEditNodeName] = useState("");
  const [isSavingNode, setIsSavingNode] = useState(false);

  // Sync refs
  useEffect(() => { rotationRef.current = rotation; }, [rotation]);
  useEffect(() => { selectedNodeRef.current = selectedNode; }, [selectedNode]);
  useEffect(() => { searchQueryRef.current = searchQuery; }, [searchQuery]);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();
  const isDraggingRef = useRef(false); // Ref per il loop di animazione

  // Sincronizza isDragging con il ref
  useEffect(() => { isDraggingRef.current = isDragging; }, [isDragging]);

  // Fetch dati GraphRAG e Inizializzazione Sfera di Fibonacci
  useEffect(() => {
    const fetchGraph = async () => {
      setIsLoading(true);
      try {
        const res = await fetch(`${serverUrl}/api/knowledge-graph`, { headers: getHeaders() });
        if (res.ok) {
          const data = await res.json();
          
          const replacePgName = (text: string) => text.replace(/\{\{nome_pg\}\}/gi, userName);

          // Distribuzione Sfera di Fibonacci (3D)
          const numNodes = data.nodes.length;
          const phi = Math.PI * (3 - Math.sqrt(5)); // Golden angle
          const radius = 350; // Raggio della sfera

          const initNodes = data.nodes.map((n: any, i: number) => {
            const y = 1 - (i / (numNodes - 1)) * 2; // y va da 1 a -1
            const r = Math.sqrt(1 - y * y);
            const theta = phi * i;

            return {
              ...n,
              id: replacePgName(n.id),
              baseX: Math.cos(theta) * r * radius,
              baseY: y * radius,
              baseZ: Math.sin(theta) * r * radius,
              x: 0, y: 0, z: 0, screenX: 0, screenY: 0, scale: 1
            };
          });
          
          const initLinks = data.links.map((l: any) => ({
            ...l,
            source: replacePgName(l.source),
            target: replacePgName(l.target),
            label: replacePgName(l.label)
          }));

          setNodes(initNodes);
          physicsNodesRef.current = initNodes;
          setLinks(initLinks);
        }
      } catch (e) {
        console.error("Errore fetch GraphRAG:", e);
      } finally {
        setIsLoading(false);
      }
    };
    fetchGraph();
  }, [serverUrl, userName]);

  // Motore di Proiezione 3D e Render Loop
  useEffect(() => {
    if (nodes.length === 0 || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    const fov = 800; // Campo visivo (Prospettiva)

    const render3D = () => {
      const currentNodes = physicsNodesRef.current;
      const currentSearch = searchQueryRef.current;
      const currentSelected = selectedNodeRef.current;

      // Auto-rotazione se non stiamo trascinando
      if (!isDraggingRef.current) {
          rotationRef.current.y -= 0.002; // Rotazione lenta sull'asse Y
          setRotation({ ...rotationRef.current });
      }

      const rotX = rotationRef.current.x;
      const rotY = rotationRef.current.y;

      const sinX = Math.sin(rotX);
      const cosX = Math.cos(rotX);
      const sinY = Math.sin(rotY);
      const cosY = Math.cos(rotY);

      // 1. Calcolo Matrici di Rotazione e Proiezione 2D
      currentNodes.forEach(n => {
        // Rotazione asse X (Pitch)
        const y1 = n.baseY! * cosX - n.baseZ! * sinX;
        const z1 = n.baseY! * sinX + n.baseZ! * cosX;

        // Rotazione asse Y (Yaw)
        const x2 = n.baseX! * cosY + z1 * sinY;
        const z2 = -n.baseX! * sinY + z1 * cosY;

        n.x = x2;
        n.y = y1;
        n.z = z2;

        // Proiezione Prospettica
        const scale = fov / (fov + z2);
        n.screenX = (width / 2) + (x2 * scale);
        n.screenY = (height / 2) + (y1 * scale);
        n.scale = scale;
      });

      // 2. Z-Sorting (Disegna prima i nodi più lontani)
      const sortedNodes = [...currentNodes].sort((a, b) => b.z! - a.z!);

      ctx.clearRect(0, 0, width, height);

      // 3. Disegno Connessioni (Links)
      links.forEach(link => {
        const source = currentNodes.find(n => n.id === link.source);
        const target = currentNodes.find(n => n.id === link.target);
        
        if (source && target) {
          // Calcola la profondità media del link per l'opacità
          const avgZ = (source.z! + target.z!) / 2;
          const linkScale = fov / (fov + avgZ);
          
          // Nascondi i link troppo lontani o dietro la sfera per pulizia visiva
          if (avgZ > 150) return;

          // Opacità basata sulla profondità (più lontano = più trasparente)
          const opacity = Math.max(0.05, Math.min(0.4, linkScale * 0.3));
          
          ctx.beginPath();
          ctx.moveTo(source.screenX!, source.screenY!);
          ctx.lineTo(target.screenX!, target.screenY!);
          ctx.strokeStyle = `rgba(236, 72, 153, ${opacity})`;
          ctx.lineWidth = 1.5 * linkScale;
          ctx.stroke();
          
          // Disegna etichetta link solo se è abbastanza vicino
          if (avgZ < 0) {
              const midX = (source.screenX! + target.screenX!) / 2;
              const midY = (source.screenY! + target.screenY!) / 2;
              ctx.fillStyle = `rgba(255, 255, 255, ${opacity * 1.5})`;
              ctx.font = `${8 * linkScale}px monospace`;
              ctx.fillText(link.label, midX, midY);
          }
        }
      });

      // 4. Disegno Nodi
      sortedNodes.forEach(n => {
        const isHighlighted = currentSearch && n.id.toLowerCase().includes(currentSearch.toLowerCase());
        const isSelected = currentSelected === n.id;
        
        // Opacità e dimensione basate sulla profondità (Z)
        const depthOpacity = Math.max(0.2, Math.min(1, n.scale!));
        const baseRadius = isHighlighted || isSelected ? 12 : 6;
        const radius = baseRadius * n.scale!;

        ctx.beginPath();
        ctx.arc(n.screenX!, n.screenY!, radius, 0, 2 * Math.PI);
        
        if (isSelected) {
            ctx.fillStyle = `rgba(34, 197, 94, ${depthOpacity})`; // Verde
        } else if (isHighlighted) {
            ctx.fillStyle = `rgba(236, 72, 153, ${depthOpacity})`; // Rosa Airis
        } else {
            // Nodi lontani sono più scuri
            const b = Math.floor(255 * depthOpacity);
            ctx.fillStyle = `rgba(59, 130, 246, ${depthOpacity})`; // Blu
        }
        ctx.fill();
        
        // Disegna il testo solo per i nodi sulla metà frontale della sfera o se selezionati
        if (n.z! < 50 || isHighlighted || isSelected) {
            const fontSize = (isHighlighted || isSelected ? 14 : 11) * n.scale!;
            ctx.font = `${isHighlighted || isSelected ? 'bold' : 'normal'} ${fontSize}px sans-serif`;
            const textWidth = ctx.measureText(n.id).width;
            
            // Sfondo testo
            ctx.fillStyle = `rgba(0, 0, 0, ${depthOpacity * 0.8})`;
            ctx.fillRect(
                n.screenX! + (8 * n.scale!), 
                n.screenY! - (10 * n.scale!), 
                textWidth + (8 * n.scale!), 
                (20 * n.scale!)
            );

            // Testo
            ctx.fillStyle = isHighlighted || isSelected ? "#ffffff" : `rgba(255, 255, 255, ${depthOpacity})`;
            ctx.fillText(n.id, n.screenX! + (12 * n.scale!), n.screenY! + (4 * n.scale!));
        }
      });

      animationRef.current = requestAnimationFrame(render3D);
    };

    render3D();

    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, [nodes.length, links]);

  // --- HANDLERS INTERATTIVITÀ 3D CANVAS ---
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDragging(true);
    setHasMoved(false);
    setDragStart({ x: e.clientX, y: e.clientY });
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDragging) return;
    
    const dx = e.clientX - dragStart.x;
    const dy = e.clientY - dragStart.y;
    
    // Se si muove più di 3 pixel, consideralo un drag e non un click
    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
        setHasMoved(true);
    }

    // Sensibilità della rotazione
    const sensitivity = 0.005;
    
    setRotation(prev => ({
      x: prev.x + dy * sensitivity,
      y: prev.y + dx * sensitivity
    }));
    
    setDragStart({ x: e.clientX, y: e.clientY });
  };

  const handleMouseUp = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDragging(false);
    
    // Se non si è mosso (o si è mosso pochissimo), è un click!
    if (!hasMoved) {
        handleCanvasClick(e);
    }
  };

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    
    // Calcolo esatto della scala tra CSS e risoluzione interna del canvas
    const scaleX = canvasRef.current.width / rect.width;
    const scaleY = canvasRef.current.height / rect.height;

    const clickX = (e.clientX - rect.left) * scaleX;
    const clickY = (e.clientY - rect.top) * scaleY;

    // Cerca il nodo cliccato (dando priorità a quelli più vicini alla telecamera, z minore)
    const sortedNodes = [...physicsNodesRef.current].sort((a, b) => a.z! - b.z!);
    
    const clickedNode = sortedNodes.find(n => {
      // Ignora i nodi troppo lontani sul retro della sfera
      if (n.z! > 100) return false;

      // 1. Controllo collisione con il cerchio (Pallino)
      const dx = n.screenX! - clickX;
      const dy = n.screenY! - clickY;
      const radius = 12 * n.scale!;
      const inCircle = Math.sqrt(dx * dx + dy * dy) < radius + 5; // +5 pixel di tolleranza
      
      // 2. Controllo collisione con l'etichetta di testo (Bounding Box)
      const textWidthBase = (n.id.length * 7) * n.scale!; 
      const boxX = n.screenX! + (8 * n.scale!);
      const boxY = n.screenY! - (10 * n.scale!);
      const boxW = textWidthBase + (8 * n.scale!);
      const boxH = 24 * n.scale!; 
      
      const inBox = clickX >= boxX && clickX <= boxX + boxW && clickY >= boxY && clickY <= boxY + boxH;
      
      return inCircle || inBox;
    });

    if (clickedNode) {
      setSelectedNode(clickedNode.id);
      setEditNodeName(clickedNode.id);
      setIsNodeDialogOpen(true);
    } else {
      setSelectedNode(null);
    }
  };

  // --- HANDLERS CRUD NODI ---
  const handleSaveNode = async () => {
    if (!selectedNode || !editNodeName.trim() || editNodeName === selectedNode) return;
    setIsSavingNode(true);
    try {
      const res = await fetch(`${serverUrl}/api/knowledge-graph/node`, {
        method: 'PUT',
        headers: { ...getHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ old_name: selectedNode, new_name: editNodeName.trim() })
      });
      if (!res.ok) throw new Error("Errore aggiornamento nodo");
      
      // Aggiorna stato locale
      setNodes(prev => prev.map(n => n.id === selectedNode ? { ...n, id: editNodeName.trim() } : n));
      setLinks(prev => prev.map(l => ({
        ...l,
        source: l.source === selectedNode ? editNodeName.trim() : l.source,
        target: l.target === selectedNode ? editNodeName.trim() : l.target
      })));
      
      toast.success(t("knowledge_graph.toast_node_updated", { defaultValue: "Nodo aggiornato con successo." }));
      setIsNodeDialogOpen(false);
      setSelectedNode(null);
    } catch (e) {
      toast.error(t("knowledge_graph.err_update_node", { defaultValue: "Impossibile aggiornare il nodo." }));
    } finally {
      setIsSavingNode(false);
    }
  };

  const handleDeleteNode = async () => {
    if (!selectedNode) return;
    if (!confirm(t("knowledge_graph.confirm_delete", { defaultValue: "Sei sicuro di voler eliminare questo nodo e tutte le sue connessioni?" }))) return;
    
    setIsSavingNode(true);
    try {
      const res = await fetch(`${serverUrl}/api/knowledge-graph/node?name=${encodeURIComponent(selectedNode)}`, {
        method: 'DELETE',
        headers: getHeaders()
      });
      if (!res.ok) throw new Error("Errore eliminazione nodo");
      
      // Aggiorna stato locale
      setNodes(prev => prev.filter(n => n.id !== selectedNode));
      setLinks(prev => prev.filter(l => l.source !== selectedNode && l.target !== selectedNode));
      
      toast.success(t("knowledge_graph.toast_node_deleted", { defaultValue: "Nodo eliminato con successo." }));
      setIsNodeDialogOpen(false);
      setSelectedNode(null);
    } catch (e) {
      toast.error(t("knowledge_graph.err_delete_node", { defaultValue: "Impossibile eliminare il nodo." }));
    } finally {
      setIsSavingNode(false);
    }
  };

  return (
    <div className="flex flex-col h-full space-y-4">
      <div className="space-y-1 border-b border-white/10 pb-2 shrink-0">
        <h3 className="text-lg font-medium flex items-center gap-2 text-primary">
          <Network className="w-5 h-5" /> {t("knowledge_graph.tab_soul", { defaultValue: "Mappa dell'Anima (GraphRAG)" })}
        </h3>
        <p className="text-xs text-muted-foreground">
          {t("knowledge_graph.desc", { defaultValue: "Esplora la rete neurale dei ricordi dell'Anima." })}
        </p>
      </div>

      <div className="flex-1 flex flex-col min-h-0 m-0 relative rounded-lg border border-white/10 overflow-hidden">
        <div className="absolute top-4 left-4 right-4 z-10 flex gap-2">
            <div className="relative flex-1 max-w-xs">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input 
                    placeholder={t("knowledge_graph.search", { defaultValue: "Cerca entità..." })}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-8 bg-background/80 backdrop-blur-sm border-white/20"
                />
                {searchQuery && (
                    <Button variant="ghost" size="icon" className="absolute right-1 top-1 h-7 w-7" onClick={() => setSearchQuery("")}>
                        <X className="h-3 w-3" />
                    </Button>
                )}
            </div>
            <div className="bg-background/80 backdrop-blur-sm border border-white/20 rounded-md px-3 py-1.5 flex items-center gap-3 text-xs font-mono text-muted-foreground">
                <span>{t("knowledge_graph.nodes", { defaultValue: "Nodi" })}: {nodes.length}</span>
                <span>{t("knowledge_graph.links", { defaultValue: "Connessioni" })}: {links.length}</span>
            </div>
        </div>

        {isLoading ? (
            <div className="flex-1 flex items-center justify-center bg-black/50">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
        ) : nodes.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground bg-black/50">
                <Network className="w-12 h-12 mb-4 opacity-20" />
                <p>{t("knowledge_graph.no_data", { defaultValue: "Nessun ricordo relazionale trovato." })}</p>
            </div>
        ) : (
            <div className="flex-1 w-full h-full bg-black/50 relative overflow-hidden">
                <canvas 
                    ref={canvasRef} 
                    width={1200} 
                    height={800} 
                    className="w-full h-full cursor-grab active:cursor-grabbing"
                    onMouseDown={handleMouseDown}
                    onMouseMove={handleMouseMove}
                    onMouseUp={handleMouseUp}
                    onMouseLeave={handleMouseUp}
                />
                {/* Overlay Istruzioni 3D */}
                <div className="absolute bottom-4 right-4 bg-background/80 backdrop-blur-sm px-3 py-1.5 rounded-md border border-white/10 text-[10px] text-muted-foreground pointer-events-none">
                    Trascina per ruotare il globo
                </div>
            </div>
        )}
      </div>

      {/* DIALOGO MODIFICA NODO GRAPHRAG */}
      <Dialog open={isNodeDialogOpen} onOpenChange={setIsNodeDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-primary">
              <Edit className="w-5 h-5" /> {t("knowledge_graph.edit_node", { defaultValue: "Modifica Nodo" })}
            </DialogTitle>
            <DialogDescription>
              {t("knowledge_graph.edit_node_desc", { defaultValue: "Modifica il nome dell'entità o eliminala dalla memoria dell'Anima." })}
            </DialogDescription>
          </DialogHeader>
          <div className="py-4 space-y-4">
            <div className="space-y-2">
              <Label>{t("knowledge_graph.node_name", { defaultValue: "Nome Entità" })}</Label>
              <Input 
                value={editNodeName} 
                onChange={(e) => setEditNodeName(e.target.value)} 
                className="font-mono"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground uppercase tracking-wider">{t("knowledge_graph.connections", { defaultValue: "Connessioni" })}</Label>
              <div className="max-h-[150px] overflow-y-auto bg-muted/10 border border-white/5 rounded-md p-2 text-xs font-mono space-y-1">
                {links.filter(l => l.source === selectedNode || l.target === selectedNode).map((l, i) => (
                  <div key={i} className="truncate text-muted-foreground">
                    {l.source === selectedNode ? (
                      <><span className="text-primary">{l.source}</span> <span className="text-pink-400">{l.label}</span> {l.target}</>
                    ) : (
                      <>{l.source} <span className="text-pink-400">{l.label}</span> <span className="text-primary">{l.target}</span></>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter className="flex justify-between sm:justify-between">
            <Button variant="destructive" onClick={handleDeleteNode} disabled={isSavingNode}>
              {isSavingNode ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Trash2 className="w-4 h-4 mr-2" />}
              {t("knowledge_graph.btn_delete", { defaultValue: "Elimina Nodo" })}
            </Button>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setIsNodeDialogOpen(false)} disabled={isSavingNode}>
                {t("knowledge_graph.btn_cancel", { defaultValue: "Annulla" })}
              </Button>
              <Button onClick={handleSaveNode} disabled={isSavingNode || !editNodeName.trim() || editNodeName === selectedNode}>
                {isSavingNode ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Save className="w-4 h-4 mr-2" />}
                {t("knowledge_graph.btn_save", { defaultValue: "Salva" })}
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};