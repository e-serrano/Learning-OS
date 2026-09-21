interface PlaceholderProps {
  title: string
}

/** Stand-in for a page a later task (T111-T119) replaces with real
 * content -- T109's job is only the route existing and being reachable. */
export function Placeholder({ title }: PlaceholderProps) {
  return (
    <div className="placeholder">
      <h2>{title}</h2>
      <p>Coming soon.</p>
    </div>
  )
}
