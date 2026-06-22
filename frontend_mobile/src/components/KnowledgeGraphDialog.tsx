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
  weight?: number;
  category?: string; // [NUOVO] Categoria dominante del nodo
}

interface GraphLink {
  source: string;
  target: string;
  label: string;
  context?: string; // [NUOVO] Contesto per i filtri
}

export const KnowledgeGraphDialog = ({ serverUrl, userName }: KnowledgeGraphDialogProps) => {
  const { t } = useTranslation();
  const [isLoading, setIsLoading] = useState(false);
  const [nodes, setNodes] = useState<GraphNode[]>(Array(0));
  const [links, setLinks] = useState<GraphLink[]>(Array(0));
  const [searchQuery, setSearchQuery] = useState("");
  
  // --- [NUOVO] STATI PER FILTRI E ZOOM ---
  const [zoom, setZoom] = useState(1);
  const [filterAvatar, setFilterAvatar] = useState(true);
  const [filterLearning, setFilterLearning] = useState(true);
  // Rimosso filtro RPG (Accorpato ad Avatar)
  
  // Ref mutabile per la fisica, disaccoppiato dallo stato React per evitare lag e desync
  const physicsNodesRef = useRef<GraphNode[]>(Array(0));
  const selectedNodeRef = useRef<string | null>(null);
  const searchQueryRef = useRef("");
  const zoomRef = useRef(1);
  const filtersRef = useRef({ avatar: true, learning: true });

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
  useEffect(() => { zoomRef.current = zoom; }, [zoom]);
  useEffect(() => { filtersRef.current = { avatar: filterAvatar, learning: filterLearning }; }, [filterAvatar, filterLearning]);

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

          // --- [FIX CRITICO] EURISTICA DEL CONTESTO (SEMPLIFICATA) ---
          const getLinkCategory = (contextStr: string | null | undefined) => {
              const ctx = (contextStr || "").toLowerCase().trim();

              // Se non c'è contesto, o se appartiene a una chat (Standard o GDR), è Avatar (Blu)
              if (!ctx || ctx === "null" || ctx === "undefined") return 'avatar';
              if (ctx.startsWith('standard') || ctx.includes('realtà') || ctx.startsWith('rpg') || ctx.includes('gdr') || ctx.includes('terra24') || ctx.includes('aincrad')) return 'avatar';
              
              // Tutto il resto (Studio, Wiki, Codice) è Learning (Giallo)
              return 'learning';
          };

          // Calcolo del "peso" e della "categoria dominante" di ogni nodo
          const nodeWeights: Record<string, number> = {};
          const nodeCats: Record<string, string> = {};

          data.links.forEach((l: any) => {
            nodeWeights[l.source] = (nodeWeights[l.source] || 0) + 1;
            nodeWeights[l.target] = (nodeWeights[l.target] || 0) + 1;

            const cat = getLinkCategory(l.context);
            // Priorità visiva: Avatar > Learning
            if (!nodeCats[l.source] || cat === 'avatar') nodeCats[l.source] = cat;
            if (!nodeCats[l.target] || cat === 'avatar') nodeCats[l.target] = cat;
          });

          // Distribuzione Sfera di Fibonacci Estesa (3D Anti-Clutter)
          const numNodes = data.nodes.length;
          const phi = Math.PI * (3 - Math.sqrt(5)); // Golden angle
          const radius = numNodes > 500 ? 1200 : (numNodes > 100 ? 800 : 400);

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
              x: 0, y: 0, z: 0, screenX: 0, screenY: 0, scale: 1,
              weight: nodeWeights[n.id] || 0,
              category: nodeCats[n.id] || 'avatar'
            };
          });
          
          const initLinks = data.links.map((l: any) => ({
            ...l,
            source: replacePgName(l.source),
            target: replacePgName(l.target),
            label: replacePgName(l.label),
            context: l.context
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
    
    // --- [FIX CRITICO MATEMATICO] ANTI-CRASH CANVAS ---
    // Se il raggio della sfera è 1200, la profondità (Z) può arrivare a -1200.
    // Se fov è 1000, la formula scale = fov / (fov + z) dà 1000 / (1000 - 1200) = -5!
    // Un raggio negativo fa crashare istantaneamente il canvas (IndexSizeError).
    // Impostiamo il FOV a 3000 per garantire che la telecamera sia SEMPRE fuori dalla sfera.
    const fov = 3000; 

    // Variabile per l'Hover tracking
    let hoveredNodeId: string | null = null;
    let connectedToHovered: Set<string> = new Set();

    // Event listener per catturare la posizione del mouse (Hover)
    const handleCanvasMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      const scaleX = canvas.width / rect.width;
      const scaleY = canvas.height / rect.height;
      const mouseX = (e.clientX - rect.left) * scaleX;
      const mouseY = (e.clientY - rect.top) * scaleY;

      const currentNodes = physicsNodesRef.current;
      // Cerca il nodo più vicino sotto il mouse
      const found = currentNodes.find(n => {
          if (n.z! > 300) return false; // Ignora nodi sul retro
          const dx = n.screenX! - mouseX;
          const dy = n.screenY! - mouseY;
          // Area di hit dinamica basata sul peso
          const hitRadius = (Math.min(15, 6 + (n as any).weight * 0.5)) * n.scale! + 5;
          return Math.sqrt(dx * dx + dy * dy) < hitRadius;
      });

      if (found) {
          hoveredNodeId = found.id;
          // Calcola chi è connesso a lui
          const connected = new Set<string>();
          links.forEach(l => {
              if (l.source === found.id) connected.add(l.target);
              if (l.target === found.id) connected.add(l.source);
          });
          connectedToHovered = connected;
      } else {
          hoveredNodeId = null;
          connectedToHovered.clear();
      }
    };

    canvas.addEventListener('mousemove', handleCanvasMouseMove);

    const render3D = () => {
      const currentNodes = physicsNodesRef.current;
      const currentSearch = searchQueryRef.current;
      const currentSelected = selectedNodeRef.current;
      const currentZoom = zoomRef.current;
      const currentFilters = filtersRef.current;

      // --- [FIX CRITICO] IDENTIFICAZIONE DELLE CATEGORIE DEI LINK (SEMPLIFICATA) ---
      const getLinkCategory = (contextStr: string | null | undefined) => {
          const ctx = (contextStr || "").toLowerCase().trim();
          if (!ctx || ctx === "null" || ctx === "undefined") return 'avatar';
          if (ctx.startsWith('standard') || ctx.includes('realtà') || ctx.startsWith('rpg') || ctx.includes('gdr') || ctx.includes('terra24') || ctx.includes('aincrad')) return 'avatar';
          return 'learning';
      };

      // 1. Filtra i link in base ai checkbox attivi
      const activeLinks = links.filter(link => {
          const cat = getLinkCategory(link.context);
          if (cat === 'avatar' && !currentFilters.avatar) return false;
          if (cat === 'learning' && !currentFilters.learning) return false;
          return true;
      });

      // Calcola quanti filtri sono attivi per fare il Boost dell'Opacità
      const activeFilterCount = (currentFilters.avatar ? 1 : 0) + (currentFilters.learning ? 1 : 0);
      const opacityBoost = activeFilterCount < 2 ? 2.5 : 1.0;

      // 2. Crea un Set di nodi "vivi" (quelli che hanno almeno un link attivo)
      const activeNodeIds = new Set<string>();
      activeLinks.forEach(l => {
          activeNodeIds.add(l.source);
          activeNodeIds.add(l.target);
      });

      // Seleziona i nodi connessi a quello attivo per l'highlight
      const connectedToSelected = new Set<string>();
      if (currentSelected) {
          activeLinks.forEach(l => {
              if (l.source === currentSelected) connectedToSelected.add(l.target);
              if (l.target === currentSelected) connectedToSelected.add(l.source);
          });
      }

      // Auto-rotazione fluida
      if (!isDraggingRef.current && !hoveredNodeId) {
          rotationRef.current.y -= 0.001;
          setRotation({ ...rotationRef.current });
      }

      const rotX = rotationRef.current.x;
      const rotY = rotationRef.current.y;
      const sinX = Math.sin(rotX), cosX = Math.cos(rotX);
      const sinY = Math.sin(rotY), cosY = Math.cos(rotY);

      // 3. Matrici di Rotazione, Proiezione 2D e ZOOM
      currentNodes.forEach(n => {
        const y1 = n.baseY! * cosX - n.baseZ! * sinX;
        const z1 = n.baseY! * sinX + n.baseZ! * cosX;
        const x2 = n.baseX! * cosY + z1 * sinY;
        const z2 = -n.baseX! * sinY + z1 * cosY;

        n.x = x2; n.y = y1; n.z = z2;

        const scale = (fov / (fov + z2)) * currentZoom; // [FIX ZOOM] Applica fattore di scala
        n.screenX = (width / 2) + (x2 * scale);
        n.screenY = (height / 2) + (y1 * scale);
        n.scale = scale;
      });

      // Z-Sorting per rendering corretto
      const sortedNodes = [...currentNodes].sort((a, b) => b.z! - a.z!);

      // Sfondo galattico scuro
      ctx.fillStyle = "#09090b"; 
      ctx.fillRect(0, 0, width, height);

      // 4. Disegno Connessioni (Links)
      activeLinks.forEach(link => {
        const source = currentNodes.find(n => n.id === link.source);
        const target = currentNodes.find(n => n.id === link.target);
        
        if (source && target) {
          const avgZ = (source.z! + target.z!) / 2;
          if (avgZ > 400) return; // Culling profondo

          const linkScale = (fov / (fov + avgZ)) * currentZoom;
          const isLinkHighlighted = 
              (currentSelected && (link.source === currentSelected || link.target === currentSelected)) ||
              (hoveredNodeId && (link.source === hoveredNodeId || link.target === hoveredNodeId));

          const cat = getLinkCategory(link.context);
          
          // Colori Base per Categoria (Semplificati)
          let r = 59, g = 130, b = 246; // Avatar & RPG (Blu)
          if (cat === 'learning') { r = 234; g = 179; b = 8; } // Learning (Giallo)

          // [FIX OPACITÀ] Applica il boost se l'utente sta filtrando
          let opacity = Math.max(0.05, Math.min(0.25, linkScale * 0.15)) * opacityBoost;
          let lineWidth = 0.5 * linkScale;
          let color = `rgba(${r}, ${g}, ${b}, ${opacity})`;

          if (isLinkHighlighted) {
              opacity = 0.9 * linkScale;
              lineWidth = 2.0 * linkScale;
              color = `rgba(${r}, ${g}, ${b}, ${opacity})`;
          }
          
          ctx.beginPath();
          ctx.moveTo(source.screenX!, source.screenY!);
          ctx.lineTo(target.screenX!, target.screenY!);
          ctx.strokeStyle = color;
          ctx.lineWidth = lineWidth;
          ctx.stroke();
          
          if (isLinkHighlighted && avgZ < 100) {
              const midX = (source.screenX! + target.screenX!) / 2;
              const midY = (source.screenY! + target.screenY!) / 2;
              ctx.fillStyle = `rgba(255, 255, 255, ${opacity})`;
              ctx.font = `${10 * linkScale}px monospace`;
              ctx.fillText(link.label, midX, midY - 5);
          }
        }
      });

      // 5. Disegno Nodi
      sortedNodes.forEach(n => {
        // [FIX FILTRI] Salta il rendering dei nodi che non hanno connessioni attive
        if (!activeNodeIds.has(n.id)) return;

        const weight = (n as any).weight || 0;
        const cat = n.category || 'avatar';
        const isSearchHighlighted = currentSearch && n.id.toLowerCase().includes(currentSearch.toLowerCase());
        const isSelected = currentSelected === n.id;
        const isConnectedToSelected = connectedToSelected.has(n.id);
        const isHovered = hoveredNodeId === n.id;
        const isConnectedToHovered = connectedToHovered.has(n.id);
        
        const shouldShowText = isSearchHighlighted || isSelected || isConnectedToSelected || isHovered || isConnectedToHovered;

        const depthOpacity = Math.max(0.1, Math.min(1, n.scale!));
        
        let baseRadius = Math.min(15, 3 + (weight * 0.4));
        if (isSearchHighlighted || isHovered || isSelected) baseRadius += 4;
        
        // --- [FIX CRITICO MATEMATICO] SAFE CLAMPING ---
        const radius = Math.max(0.1, baseRadius * n.scale!);

        // Assegnazione colori ai nodi in base alla categoria (Semplificati)
        let r = 59, g = 130, b = 246; // Avatar & RPG (Blu)
        if (cat === 'learning') { r = 234; g = 179; b = 8; }

        ctx.beginPath();
        ctx.arc(n.screenX!, n.screenY!, radius, 0, 2 * Math.PI);
        
        if (isSelected) {
            ctx.fillStyle = `rgba(34, 197, 94, ${depthOpacity})`;
            ctx.shadowBlur = 15; ctx.shadowColor = "rgba(34, 197, 94, 0.8)";
        } else if (isHovered || isSearchHighlighted) {
            ctx.fillStyle = `rgba(255, 255, 255, ${depthOpacity})`; 
            ctx.shadowBlur = 10; ctx.shadowColor = "rgba(255, 255, 255, 0.8)";
        } else if (isConnectedToSelected || isConnectedToHovered) {
            ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${depthOpacity * 0.9})`; // Colore Categoria Acceso
            ctx.shadowBlur = 0;
        } else {
            // [FIX COLORI NODI] Ora i nodi base hanno il colore della loro categoria, non grigio scuro
            ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${depthOpacity * 0.5})`; 
            ctx.shadowBlur = 0;
        }
        ctx.fill();
        ctx.shadowBlur = 0;
        
        if (shouldShowText && n.z! < 200) {
            const fontSize = (isHovered || isSelected ? 16 : 12) * n.scale!;
            ctx.font = `${isHovered || isSelected ? 'bold' : 'normal'} ${fontSize}px sans-serif`;
            const textWidth = ctx.measureText(n.id).width;
            
            ctx.fillStyle = `rgba(0, 0, 0, ${depthOpacity * 0.9})`;
            ctx.roundRect(
                n.screenX! + (radius * 1.2), 
                n.screenY! - (fontSize * 0.8), 
                textWidth + 10, 
                fontSize * 1.5,
                4
            );
            ctx.fill();

            ctx.fillStyle = isHovered || isSelected || isSearchHighlighted ? "#ffffff" : `rgba(200, 200, 200, ${depthOpacity})`;
            ctx.fillText(n.id, n.screenX! + (radius * 1.2) + 5, n.screenY! + (fontSize * 0.3));
        }
      });

      animationRef.current = requestAnimationFrame(render3D);
    };

    render3D();

    return () => {
      canvas.removeEventListener('mousemove', handleCanvasMouseMove);
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
        <div className="absolute top-4 left-4 right-4 z-10 flex flex-col gap-2 pointer-events-none">
            {/* RAW 1: Search and Stats */}
            <div className="flex gap-2 pointer-events-auto">
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
                    <span className="text-primary ml-2 border-l border-white/10 pl-3">Zoom: {Math.round(zoom * 100)}%</span>
                </div>
            </div>
            
            {/* RAW 2: Filters */}
            <div className="flex gap-2 pointer-events-auto">
                <Button 
                    variant={filterAvatar ? "default" : "outline"} 
                    size="sm" 
                    className={"text-xs h-7 " + (filterAvatar ? "bg-blue-600 hover:bg-blue-700 text-white" : "")}
                    onClick={() => setFilterAvatar(!filterAvatar)}
                >
                    <span className="w-2 h-2 rounded-full bg-blue-300 mr-2"></span> Avatar / RPG
                </Button>
                <Button 
                    variant={filterLearning ? "default" : "outline"} 
                    size="sm" 
                    className={"text-xs h-7 " + (filterLearning ? "bg-yellow-600 hover:bg-yellow-700 text-white" : "")}
                    onClick={() => setFilterLearning(!filterLearning)}
                >
                    <span className="w-2 h-2 rounded-full bg-yellow-300 mr-2"></span> Self-Learning
                </Button>
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
                    onWheel={(e) => {
                        e.preventDefault();
                        const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
                        setZoom(prev => Math.max(0.1, Math.min(10.0, prev * zoomFactor)));
                    }}
                />
                {/* Overlay Istruzioni 3D */}
                <div className="absolute bottom-4 right-4 bg-background/80 backdrop-blur-sm px-3 py-1.5 rounded-md border border-white/10 text-[10px] text-muted-foreground pointer-events-none">
                    Trascina per ruotare | Rotellina per Zoom
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
              <div className="max-h-[150px] overflow-y-auto bg-muted/10 border border-white/5 rounded-md p-2 text-xs font-mono space-y-1 custom-scrollbar">
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