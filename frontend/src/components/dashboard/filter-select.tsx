import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface FilterSelectProps {
  value: string | undefined;
  onValueChange: (value: string | undefined) => void;
  placeholder: string;
  options: { value: string; label: string }[];
  allLabel?: string;
  className?: string;
}

export function FilterSelect({
  value,
  onValueChange,
  placeholder,
  options,
  allLabel = "Todos",
  className = "w-[160px]",
}: FilterSelectProps) {
  return (
    <Select
      value={value ?? "all"}
      onValueChange={(v) => onValueChange(v === "all" ? undefined : v)}
    >
      <SelectTrigger className={className}>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">{allLabel}</SelectItem>
        {options.map((o) => (
          <SelectItem key={o.value} value={o.value}>
            {o.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
