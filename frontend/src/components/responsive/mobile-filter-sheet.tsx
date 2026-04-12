"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetFooter, SheetTrigger } from "@/components/ui/sheet";
import { Filter } from "lucide-react";
import { useMediaQuery } from "@/hooks/use-media-query";

interface MobileFilterSheetProps {
  activeCount?: number;
  title?: string;
  onClear?: () => void;
  children: React.ReactNode;
}

export function MobileFilterSheet({
  activeCount = 0, title = "Filtros", onClear, children,
}: MobileFilterSheetProps) {
  const [open, setOpen] = useState(false);
  const isDesktop = useMediaQuery("(min-width: 1024px)");

  if (isDesktop) {
    return <>{children}</>;
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2 lg:hidden">
          <Filter className="h-4 w-4" />
          {title}{activeCount > 0 && ` (${activeCount})`}
        </Button>
      </SheetTrigger>
      <SheetContent side="bottom" className="max-h-[80vh] overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{title}</SheetTitle>
        </SheetHeader>
        <div className="space-y-4 py-4">{children}</div>
        <SheetFooter className="flex-row gap-2">
          {onClear && (
            <Button variant="outline" size="sm" className="flex-1" onClick={() => { onClear(); setOpen(false); }}>
              Limpiar
            </Button>
          )}
          <Button size="sm" className="flex-1" onClick={() => setOpen(false)}>
            Aplicar
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
