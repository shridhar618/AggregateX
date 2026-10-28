import Icon from './Icon'

const EmptyState = ({ icon = 'scan', title, children, action, compact = false }) => (
  <div className={`empty ${compact ? 'empty--compact' : ''}`}>
    <div className="empty__icon" aria-hidden="true">
      <span className="empty__ring" />
      <Icon name={icon} />
    </div>
    <h3 className="empty__title">{title}</h3>
    {children && <div className="empty__text">{children}</div>}
    {action && <div className="empty__action">{action}</div>}
  </div>
)

export default EmptyState
