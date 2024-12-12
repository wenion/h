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

  update(newState, prevState) {
    if (newState != prevState) {
      const urlSearchParams = new URLSearchParams(window.location.search);

      let page = parseInt(urlSearchParams.get("page"), 10);
      if (isNaN(page) || page < 1) {
        page = PAGE;
      }

      let pageSize = parseInt(urlSearchParams.get("pageSize"), 10);
      if (isNaN(pageSize) || pageSize < 1) {
        pageSize = PAGE_SIZE;
      }

      let sortby = urlSearchParams.get("sortby");
      if (!ALLOWED_SORTBY.includes(sortby)) {
        sortby = SORTBY; // Default value
      }

      let order = urlSearchParams.get("order");
      if (!ALLOWED_ORDER.includes(order)) {
        order = ORDER; // Default value
      }

      const url = new URL(document.location.origin + document.location.pathname);
      const params = new URLSearchParams({
        page: page.toString(),
        pageSize: pageSize.toString(),
        sortby: sortby,
        order: order
      });
      url.search = params.toString();

      document.location.href = url.toString();
    }
  }
}
