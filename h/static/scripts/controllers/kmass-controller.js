import escapeHtml from 'escape-html';

import { Controller } from '../base/controller';

const PAGE = '1';
const PAGE_SIZE = '25';
const SORTBY = 'timestamp';
const ORDER = 'desc';


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
      const urlSearchParams = new URLSearchParams(window.location.search)
      let page = urlSearchParams.get("page") ? urlSearchParams.get("page"): PAGE;
      let pageSize = urlSearchParams.get("pageSize") ? urlSearchParams.get("pageSize"): PAGE_SIZE;
      let sortby = urlSearchParams.get("sortby") ? urlSearchParams.get("sortby"): SORTBY;
      let order = urlSearchParams.get("order") ? urlSearchParams.get("order"): ORDER;
      if (newState.page) {
        page = newState.page
      }
      if (newState.pageSize) {
        pageSize = newState.pageSize
        page = PAGE
      }
      if (newState.sortby) {
        sortby = newState.sortby
        page = PAGE
      }
      if (newState.order) {
        order = newState.order
        page = PAGE
      }

      let url = document.location.origin +
        document.location.pathname +
        "?page=" + page +
        "&pageSize=" + pageSize +
        "&sortby=" + sortby +
        "&order=" + order

      document.location.href = url
    }
    
  }
}
