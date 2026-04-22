interface SectionLabelProps {
  children: React.ReactNode;
}

export function SectionLabel({ children }: SectionLabelProps) {
  return (
    <div className="mb-2 px-3 text-[11px] font-semibold tracking-widest text-muted-fg uppercase">
      {children}
    </div>
  );
}
