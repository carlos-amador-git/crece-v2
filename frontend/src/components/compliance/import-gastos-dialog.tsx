"use client";

import { useState, useCallback, useRef } from "react";
import * as XLSX from "xlsx";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Upload, Download, FileSpreadsheet, Loader2, CheckCircle2, AlertTriangle, X, XCircle } from "lucide-react";

const CATEGORIAS_INE = [
  "propaganda",
  "operativos",
  "gastos_produccion",
  "transporte",
  "alimentacion",
  "alquiler_inmuebles",
  "servicios_personales",
  "publicidad_redes",
  "otros",
] as const;

interface GastoRow {
  concepto: string;
  categoria: string;
  monto: number;
  fecha: string;
  aprobado: boolean;
  _error?: string;
}

function downloadTemplate() {
  const headers = ["concepto", "categoria", "monto", "fecha", "aprobado"];
  const example = [
    ["Impresion de volantes", "propaganda", 15000, "2024-05-15", true],
    ["Renta salon evento", "alquiler_inmuebles", 8000, "2024-05-20", true],
    ["Publicidad en Facebook", "publicidad_redes", 5000, "2024-05-22", false],
  ];
  const ws = XLSX.utils.aoa_to_sheet([headers, ...example]);
  ws["!cols"] = [{ wch: 30 }, { wch: 22 }, { wch: 12 }, { wch: 14 }, { wch: 10 }];
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Gastos");
  XLSX.writeFile(wb, "plantilla_gastos_crece.xlsx");
}

function validateRow(row: GastoRow, idx: number): string | null {
  if (!row.concepto?.trim()) return `Fila ${idx + 1}: concepto vacio`;
  if (!CATEGORIAS_INE.includes(row.categoria as any)) return `Fila ${idx + 1}: categoria invalida "${row.categoria}"`;
  if (typeof row.monto !== "number" || row.monto <= 0 || isNaN(row.monto)) return `Fila ${idx + 1}: monto invalido`;
  if (!row.fecha) return `Fila ${idx + 1}: fecha vacia`;
  return null;
}

interface ImportGastosDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ImportGastosDialog({ open, onOpenChange }: ImportGastosDialogProps) {
  const [rows, setRows] = useState<GastoRow[]>([]);
  const [dragging, setDragging] = useState(false);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<{ imported: number; errors: string[] } | null>(null);
  const [fileName, setFileName] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const reset = () => {
    setRows([]);
    setResult(null);
    setFileName("");
  };

  const processFile = useCallback((file: File) => {
    setResult(null);
    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (e) => {
      const data = new Uint8Array(e.target?.result as ArrayBuffer);
      const wb = XLSX.read(data, { type: "array" });
      const ws = wb.Sheets[wb.SheetNames[0]];
      const json = XLSX.utils.sheet_to_json<Record<string, any>>(ws);

      const parsed: GastoRow[] = json.map((r, idx) => {
        const row: GastoRow = {
          concepto: String(r.concepto ?? "").trim(),
          categoria: String(r.categoria ?? "").trim().toLowerCase(),
          monto: Number(r.monto) || 0,
          fecha: r.fecha ? formatExcelDate(r.fecha) : "",
          aprobado: r.aprobado === true || r.aprobado === "true" || r.aprobado === 1,
        };
        row._error = validateRow(row, idx) ?? undefined;
        return row;
      });
      setRows(parsed);
    };
    reader.readAsArrayBuffer(file);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) processFile(file);
  }, [processFile]);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  }, [processFile]);

  const hasErrors = rows.some((r) => r._error);
  const validRows = rows.filter((r) => !r._error);

  const handleImport = async () => {
    if (validRows.length === 0) return;
    setImporting(true);
    try {
      const payload = validRows.map(({ _error, ...rest }) => rest);
      const res = await api.post<{ imported: number; errors: string[] }>("/blindaje/gastos/import", { gastos: payload });
      setResult(res);
      queryClient.invalidateQueries({ queryKey: ["compliance-gastos"] });
      queryClient.invalidateQueries({ queryKey: ["compliance-report"] });
    } catch (err: any) {
      setResult({ imported: 0, errors: [err?.message ?? "Error de conexion"] });
    } finally {
      setImporting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) reset(); onOpenChange(o); }}>
      <DialogContent className="max-h-[85vh] max-w-3xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Importar Gastos</DialogTitle>
          <DialogDescription>
            Sube un archivo Excel (.xlsx) o CSV con los gastos de campana. Descarga la plantilla para ver el formato correcto.
          </DialogDescription>
        </DialogHeader>

        {/* Success result */}
        {result && result.imported > 0 && (
          <div className="flex items-center gap-3 rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-4">
            <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-600" />
            <div>
              <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-300">
                {result.imported} gastos importados correctamente
              </p>
              {result.errors.length > 0 && (
                <p className="text-xs text-emerald-600/80">{result.errors.length} errores omitidos</p>
              )}
            </div>
          </div>
        )}

        {/* Error result */}
        {result && result.imported === 0 && result.errors.length > 0 && (
          <div className="flex items-center gap-3 rounded-lg border border-red-500/20 bg-red-500/10 p-4">
            <AlertTriangle className="h-5 w-5 shrink-0 text-red-600" />
            <div>
              <p className="text-sm font-semibold text-red-700 dark:text-red-300">Error al importar</p>
              <p className="text-xs text-red-600/80">{result.errors[0]}</p>
            </div>
          </div>
        )}

        {/* Drop zone (shown when no rows loaded) */}
        {rows.length === 0 && !result && (
          <div
            className={`relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-12 transition-colors ${
              dragging
                ? "border-accent bg-accent/5"
                : "border-border hover:border-accent/50 hover:bg-muted/30"
            }`}
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
          >
            <Upload className="mb-3 h-10 w-10 text-muted-foreground/50" />
            <p className="text-sm font-medium">Arrastra tu archivo aqui</p>
            <p className="mt-1 text-xs text-muted-foreground">o haz click para seleccionar (.xlsx, .csv)</p>
            <input
              ref={fileRef}
              type="file"
              accept=".xlsx,.xls,.csv"
              onChange={handleFileChange}
              className="absolute inset-0 cursor-pointer opacity-0"
            />
          </div>
        )}

        {/* Preview table */}
        {rows.length > 0 && !result && (
          <>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileSpreadsheet className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">{fileName}</span>
                <Badge variant="secondary">{rows.length} filas</Badge>
                {hasErrors && (
                  <Badge variant="destructive">{rows.filter((r) => r._error).length} errores</Badge>
                )}
              </div>
              <Button variant="ghost" size="sm" onClick={reset}>
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="max-h-[40vh] overflow-auto rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[30px]">#</TableHead>
                    <TableHead>Concepto</TableHead>
                    <TableHead>Categoria</TableHead>
                    <TableHead className="text-right">Monto</TableHead>
                    <TableHead>Fecha</TableHead>
                    <TableHead className="text-center">Aprobado</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((row, i) => (
                    <TableRow key={i} className={row._error ? "bg-red-50 dark:bg-red-950/20" : ""}>
                      <TableCell className="text-xs text-muted-foreground">{i + 1}</TableCell>
                      <TableCell className="font-medium">{row.concepto || <span className="text-red-500">vacio</span>}</TableCell>
                      <TableCell>
                        {CATEGORIAS_INE.includes(row.categoria as any) ? (
                          <Badge variant="secondary">{row.categoria}</Badge>
                        ) : (
                          <Badge variant="destructive">{row.categoria || "?"}</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {row.monto > 0 ? `$${row.monto.toLocaleString()}` : <span className="text-red-500">0</span>}
                      </TableCell>
                      <TableCell className="text-sm">{row.fecha || <span className="text-red-500">-</span>}</TableCell>
                      <TableCell className="text-center">
                        {row.aprobado ? (
                          <CheckCircle2 className="mx-auto h-4 w-4 text-emerald-500" />
                        ) : (
                          <XCircle className="mx-auto h-4 w-4 text-muted-foreground/40" />
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {hasErrors && (
              <div className="space-y-1">
                {rows.filter((r) => r._error).map((r, i) => (
                  <p key={i} className="text-xs text-red-600">{r._error}</p>
                ))}
              </div>
            )}
          </>
        )}

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" onClick={downloadTemplate} className="gap-1.5">
            <Download className="h-4 w-4" />
            Descargar Plantilla
          </Button>
          {rows.length > 0 && !result && (
            <Button
              onClick={handleImport}
              disabled={importing || validRows.length === 0}
              className="gap-1.5"
            >
              {importing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Upload className="h-4 w-4" />
              )}
              Importar {validRows.length} gastos
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Convert Excel serial date or string to YYYY-MM-DD */
function formatExcelDate(value: any): string {
  if (typeof value === "number") {
    // Excel serial date
    const date = new Date((value - 25569) * 86400 * 1000);
    return date.toISOString().split("T")[0];
  }
  if (typeof value === "string") {
    // Try to parse as date
    const d = new Date(value);
    if (!isNaN(d.getTime())) return d.toISOString().split("T")[0];
    return value;
  }
  return String(value);
}
