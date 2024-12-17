import { Controller } from '../base/controller';

const PAGE = '1';
const PAGE_SIZE = '25';
const SORTBY = 'timestamp';
const ORDER = 'desc';

const ALLOWED_SORTBY = ["event_type", "timestamp", "session_id", "task_name"];
const ALLOWED_ORDER = ["asc", "desc"];

/**
 * Controller for the search bar.
 */
export class KmassController extends Controller {
  constructor(element, options = {}) {
    super(element, options);

    this.refs.pageSizeSelect.addEventListener('change', (event) => {
      this.setState({ pageSize: event.target.value });
    });

    this.refs.sortbySelect.addEventListener('change', (event) => {
      this.setState({ sortby: event.target.value });
    });

    this.refs.orderSelect.addEventListener('change', (event) => {
      this.setState({ order: event.target.value });
    });

    this.refs.paginator.addEventListener('click', (event) => {
      this.setState({ paginator: event.target.getAttribute('value') });
    });
  }
}
