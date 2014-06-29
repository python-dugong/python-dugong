.. currentmodule:: dugong

.. _coroutines:

=============
Coroutine API
=============

This section assumes some basic familiarity with coroutines. If you
don't know what they are, you are missing out a lot and should read up
on them right away (e.g. on `Wikipedia <Wikipedia_Coroutine>`_, `PEP
342`_, `PEP 380`_ and `dabeaz.com`_).

To refresh your memory: coroutines in Python are generators, and are
obtained by calling generator functions (i.e, functions that use
``yield`` in their definiton). A coroutine can be resumed by passing
it to the built-in `next` function, or calling its `~generator.send`
method.  A coroutine can pass the control flow back to the caller by
:ref:`yielding <yieldexpr>` values using the ``yield``
expression. When the coroutine eventually terminates, the last call to
`next` or `~generator.send` will raise a `StopIteration` exception,
whose *value* attribute holds the return value of the coroutine. A
coroutine *A* may also *yield from* another coroutine *B* using the
``yield from`` expression. In this case, the control flow will pass
between *A*'s caller and *B* until *B* terminates. When *B* has
terminated, its return value becomes the result of the ``yield from``
expression in *A*, and execution continues in *A*.

In Dugong, a method or function whose name begins with ``co_`` will
return a coroutine. These coroutines are non-blocking. Whenever they
need to perform an I/O operation that would block (ie., sending data
to the server or receiving data from the server), they yield a
`PollNeeded` instance instead, and expect to be resumed when the
operation can be carried out without blocking.

The `PollNeeded` instance contains information about the I/O request
that the coroutine would like to perform. The `~PollNeeded.fd`
attribute is a file descriptor, and the `~PollNeeded.mask` attribute
is an :ref:`epoll <epoll-objects>` compatible event mask. Therefore, a
very simple way to wait for a coroutine to complete is to use a
`~select.select` loop::

  from select import select, POLLIN

  # establish connection, send request, read response header

  # Create coroutine
  crt = conn.co_readall()
  try:
      while True:
          # Resume coroutine
          io_req = next(crt)

          # Coroutine has returned because I/O is not ready,
          # prepare select call
          read_fds = (io_req.fd,) if io_req.mask & POLLIN else ()
          write_fds = (io_req.fd,) if io_req.mask & POLLOUT else ()

          # Wait for I/O readiness
          select(read_fds, write_fds, ())
  except StopIteration as exc:
      # Coroutine has completed, retrieve result
      body = exc.value

This loop is in fact fully equivalent to a simple ::

  body = conn.readall()

so in this case there really wasn't much point in using a
coroutine. This is because coroutines really only make sense if you
have more than one active coroutine. However, in that case the
necessary loop construction becomes a lot more complicated. Luckily
enough, Dugong is compatible with the `asyncio` module, so you can use
the asyncio event loop to schedule your Dugong coroutines.


Using asyncio Event-Loops
=========================

In order to schedule a Dugong coroutine in an asyncio event loop, you
have to create an `asyncio.Future` for the coroutine. This is done
with the `dugong.AioFuture` class (which inherits from
`asyncio.Future`). The reason for this additional wrapper is that the
asyncio event loop, even though very powerful, does not know how to
interpret the `PollNeeded` instances that are yielded by Dugong
coroutines. It would have been possible to have Dugong coroutines
yield `asyncio.Future` instances directly, but this would have meant
to introduce a hard dependency on asyncio, which was deemend
undesirable.

Using asyncio, the above example becomes much simpler::

  import asyncio
  import atexit

  # establish connection, send request, read response header

  # Create coroutine
  crt = conn.co_readall()

  # Get a MainLoop instance from the asyncio module to switch
  # between the coroutines as needed
  loop = asyncio.get_event_loop()
  atexit.register(loop.close)

  # Create and schedule asyncio future
  fut = AioFuture(crt, loop=loop)

  # Run the event loop
  loop.run_until_complete(fut)

  # Get the result returned by the coroutine
  body = fut.result()

The generalization to multiple coroutines is now
straightforward. Suppose you want to retrieve a number of documents
from different servers. You could use threads, but this makes the
program hard to debug, and probably most of the time the threads will
be waiting for data from the server, so there is no real need to have
a truly parallel program. In this situation, coroutines are a much
better choice. They allow you to send and receive multiple requests
simultaneously, but the program flow itself is still strictly
sequential. Here's how to do it (suppose the URLs you'd like to
retrieve a stored in *url_list*)::

  import asyncio
  import atexit
  from urllib.parse import urlsplit, urlunsplit

  def get_url(host, port, path):
      conn = HTTPConnection(host, port=port)
      yield from conn.co_send_request('GET', path)
      resp = yield from conn.co_read_response()
      assert resp.status == 200
      body = yield from conn.co_readall()
      return body

  futures = []
  for url in url_list:
      o = urlsplit(url)
      # Path is obtained by removing scheme, hostname and fragment
      # identifier from the url
      path = urlunsplit(('', '') + o[2:4] + ('',))

      # Create a coroutine and future for each URL
      futures.append(AioFuture(get_url(o.hostname, o.port, path)))

  # Run coroutines
  loop = asyncio.get_event_loop()
  atexit.register(loop.close)
  loop.run_until_complete(asyncio.wait(futures))

  # Get the results
  bodies = [ x.result() for x in futures ]


When to invoke `AioFuture`
--------------------------

When creating your own coroutines, you generally have two choices:

#. You can create asyncio style coroutines, in which you wrap calls to
   Dugong coroutines into `AioFuture`, e.g.::

     # ...

     @asyncio.coroutine
     def do_stuff():
         # ...
         yield from AioFuture(conn.co_read_response())
         # ..
         buf = yield from AioFuture(conn.co_read(8192))
         # ...

         # May also call other asyncio compatible coroutines:
         yield from asyncio.sleep(1)

         # ..

     task = asyncio.Task(do_stuff)
     loop.run_until_complete(task)

   The advantage of this style is that even though you need to wrap
   every Dugong call into `AioFuture`, you can freely mix Dugong and
   other asyncio compatible coroutines.

#. You create Dugong style coroutines, and wrap them into `AioFuture`
   just before adding them to the asyncio event loop, e.g.::

     # ...

     def do_stuff():
         # ...
         yield from conn.co_read_response()
         # ..
         buf = yield from conn.co_read(8192)
         # ...
         # Other coroutines must yield PollNeeded instance, so
         # we cannot yield from asyncio compatible coroutines:
         #yield from asyncio.sleep(1) # WON'T WORK!

     fut = AioFuture(do_stuf())
     loop.run_until_complete(fut)

   The advantage of this is that you need to call `AioFuture` only
   once. The disadvantage is that you can not yield from other asyncio
   coroutines in your coroutine.

Generally it's recommended to use the style that produces more
readable code.


Building your own Event-Loop
============================

As explained before, the easiest way to schedule coroutines is to use
the asyncio module. However, Dugong coroutines have a well-defined
interface, and you can just as well write your own coroutine
scheduling loop. In this case, the asyncio module is not used at all.

Below is a simple example that uses this technique to switch execution
between two coroutines that send requests and read responses. The code
tries to retrieve a number of documents (stored in *path_list*),
stores the missing paths in *missing_documents*, and saves the
contents of the existing documents to disk. ::

    # Note: in a real application, don't forget to ensure that
    # conn.disconnect() is called eventually
    conn = HTTPConnection('somehost.com')
    missing_documents = []

    # This function returns a coroutine that sends all requests
    def send_requests():
        for path in path_list:
            yield from conn.co_send_request('GET', path)

    # This functions returns a coroutine that reads all responses
    def read_responses():
        for (i, path) in enumerate(path_list):
            resp = yield from conn.co_read_response()
            if resp.status != 200:
                missing_documents.append(resp.path)
            with open('doc_%i.dat' % i, 'wb') as fh:
                buf = yield from conn.readall()
                fh.write(buf)

    # Create coroutines
    send_request_crt = send_requests()
    read_response_crt = read_responses()

    while True:
        # Send requests until we block
        if send_request_crt:
            try:
                io_req_1 = next(send_request_crt)
            except StopIteration:
                # All requests sent
                send_request_crt = None

        # Read responses until we block
        try:
            io_req_2 = next(read_response_crt)
        except StopIteration as exc:
            # All responses read
            break

        # Wait for fds to become ready for I/O
        assert io_req_1.mask == POLLOUT
        assert io_req_2.mask == POLLIN
        select((io_req_2.fd,), (io_req_1.fd,), ())


.. _Wikipedia_Coroutine: http://en.wikipedia.org/wiki/Coroutine
.. _`PEP 342`: http://legacy.python.org/dev/peps/pep-0342/
.. _`PEP 380`: http://legacy.python.org/dev/peps/pep-0380/
.. _`dabeaz.com`:  http://dabeaz.com/coroutines/
