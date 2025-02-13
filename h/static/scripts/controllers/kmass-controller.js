import { Controller } from '../base/controller';

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

    this.refs.pagesInput.addEventListener('change', (event) => {
      this.setState({ pages: event.target.value });
    });

    this.refs.pagesInput.addEventListener('focus', (event) => {
      this.refs.exportSubmit.disabled = true;
    });

    this.refs.pagesInput.addEventListener('blur', (event) => {
      this.refs.exportSubmit.disabled = false;
    });

  }

  update(newState, prevState) {
    if (newState != prevState) {
      const url = new URL(this.refs.linkAnchor.href)

      if (newState.paginator) {
        url.searchParams.set('page', newState.paginator);
      }
      if (newState.pageSize) {
        url.searchParams.set('pageSize', newState.pageSize);
      }
      if (newState.sortby) {
        url.searchParams.set('sortby', newState.sortby);
      }
      if (newState.order) {
        url.searchParams.set('order', newState.order);
      }
      if (newState.pages) {
        url.searchParams.set('pages', newState.pages);
      }

      this.refs.linkAnchor.href = url.toString();
      this.refs.linkAnchor.click();
    }
    
  }
}
